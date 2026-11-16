// Fast combo search for NES Dr. Mario. Exact ports of drm/gen.py (level generation) and drm/board.py
// (drops, matches, cascades), the drop-only move model of drm/plan.py, and a beam search over a level's
// pill sequence that records every placement whose cascade kills many viruses. Python (drm/, tools/)
// stays the reference: tools/check_engine.py compares the two, tools/verify_combo.py checks the glitch
// timing of what this finds.
//
// Modes (key=value args):
//   dm version                   print the build version (stamped from ../VERSION by build.bat)
//   dm resolve                   stdin: 256-byte boards as hex, one per line; stdout: "kills after_hex"
//   dm play n=N level=L plan="r,x r,x ..."   kills per pill and the final board
//   dm search level=L n0=A n1=B depth=D beam=W [min=K per=P look=1 any=0 shape=0.05 waste=2 height=1 first=1]
//                                stdout: one JSON line per recorded combo
//                                pad=1: record only combos that pass pad_ok
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

#ifndef DM_VERSION
#define DM_VERSION "dev"
#endif

typedef uint8_t u8;
enum { EMPTY = 0xFF, TOP = 0x40, BOTTOM = 0x50, LEFT = 0x60, RIGHT = 0x70, SINGLE = 0x80,
       CLEARED = 0xB0, VIRUS = 0xD0, JUST_EMPTIED = 0xF0 };

// ---------------------------------------------------------------- generation (drm/gen.py)
static uint16_t rstep(uint16_t r) { unsigned bit = ((r >> 9) ^ (r >> 1)) & 1; return (uint16_t)((r >> 1) | (bit << 15)); }
static const uint16_t SEED = 0x8988;
static const int MAX_HEIGHT[35] = {9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 10, 10, 11, 11,
                                   12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12};
static const int VCR[16] = {0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 1};
static const int CB[4] = {1, 2, 4, 0};

struct Level { u8 field[128]; u8 reserve[128]; };

static void generate(uint16_t r, int level, Level& L) {
    int pid = 0;
    for (int x = 127; x >= 0; x--) { r = rstep(r); pid = (pid + ((r >> 8) & 15)) % 9; L.reserve[x] = (u8)pid; }
    u8 mem[160];
    memset(mem, EMPTY, sizeof mem);
    int to_add = (std::min(level, 20) + 1) * 4, maxh = MAX_HEIGHT[level];
    while (to_add) {
        int h;
        do { r = rstep(r); h = (r >> 8) & 15; } while (h > maxh);
        int pos = 8 * (15 - h) + (r & 7);
        int color = to_add & 3;
        if (color == 3) { r = rstep(r); color = VCR[r & 15]; }
        while (pos < 128) {
            if (mem[pos] != EMPTY) { pos++; continue; }
            int mask = CB[mem[pos - 16] & 3] | CB[mem[pos + 16] & 3];
            if ((pos & 7) >= 2) mask |= CB[mem[pos - 2] & 3];
            if ((pos & 7) < 6) mask |= CB[mem[pos + 2] & 3];
            if (mask == 7) { pos++; continue; }
            while (CB[color] & mask) color = color > 0 ? color - 1 : 2;
            mem[pos] = (u8)(VIRUS | color);
            to_add--;
            break;
        }
    }
    memcpy(L.field, mem, 128);
}

static uint16_t rng_at(int n) { uint16_t r = SEED; for (int i = 0; i < n; i++) r = rstep(r); return r; }

// ---------------------------------------------------------------- rules (drm/board.py)
// m is 256 bytes: field 0..127, then the RAM the routines read past it (FF).
static int check_drop(u8* m) {
    int moved = 0;
    for (int y = 127; y >= 0; y--) {
        if (m[y] >= JUST_EMPTIED) {
            m[y] = EMPTY;
            int t = (y - 8) & 0xFF;
            u8 above = m[t];
            int typ = above & 0xF0;
            if (above < 0x90 && typ != LEFT) {
                if (typ == RIGHT) {
                    if (m[(y - 1) & 0xFF] >= JUST_EMPTIED) {
                        m[y] = m[t]; m[t] = EMPTY;
                        m[(y - 1) & 0xFF] = m[(t - 1) & 0xFF]; m[(t - 1) & 0xFF] = EMPTY;
                        moved += 2;
                        y -= 1;
                    }
                } else {
                    m[y] = above; m[t] = EMPTY;
                    moved += 1;
                }
            }
        }
    }
    return moved;
}

static inline void kill(u8* m, int p, int& n) {
    if ((m[p] & 0xF0) == VIRUS) n++;
    m[p] = (u8)((m[p] & 0x0F) | CLEARED);
}

// ends (optional): ends[0] = count, then the fieldPos_last ($49) of every chain cleared.
static bool check_hor(u8* m, int& n, int* ends = nullptr) {
    bool matched = false;
    int pos = 0;
    for (;;) {
        int tmp = pos;
        if (m[pos] < JUST_EMPTIED) {
            int color = m[pos] & 0x0F, chain = 0;
            for (;;) {
                tmp++;
                if ((tmp & 7) == 0 || (m[tmp] & 0x0F) != color) break;
                chain++;
            }
            if (chain >= 3) { for (int q = pos; q < tmp; q++) kill(m, q, n); matched = true; if (ends) ends[++ends[0]] = tmp; }
            pos = tmp;
        } else pos++;
        if ((pos & 7) == 0 || (pos & 7) >= 6) {
            if (pos == 128) return matched;
            if (pos & 7) { pos = (pos & 0x78) + 8; if (pos == 128) return matched; }
        }
    }
}

static bool check_ver(u8* m, int& n, int* ends = nullptr) {
    bool matched = false;
    int pos = 0;
    for (;;) {
        int tmp = pos;
        if (m[pos] < JUST_EMPTIED) {
            int color = m[pos] & 0x0F, chain = 0;
            for (;;) {
                tmp = (tmp + 8) & 0xFF;
                if ((tmp & 0xF8) == 0 || (m[tmp] & 0x0F) != color) break;
                chain++;
            }
            if (chain >= 3) {
                for (int q = pos; q != tmp; q = (q + 8) & 0xFF) kill(m, q, n);
                matched = true;
                if (ends) ends[++ends[0]] = tmp;
            }
            pos = tmp;
        } else pos += 8;
        if (pos >= 104) { pos = (pos + 1) & 7; if (pos == 0) return matched; }
    }
}

static void update_field(u8* m) {
    for (int p = 127; p >= 0; p--) {
        u8 v = m[p];
        int typ = v & 0xF0;
        if (typ == CLEARED) m[p] = (u8)(v | JUST_EMPTIED);
        else if (typ == TOP && (m[p + 8] & 0xF0) != BOTTOM) m[p] = (u8)((v & 0x0F) | SINGLE);
        else if (typ == BOTTOM && (m[(p - 8) & 0xFF] & 0xF0) != TOP) m[p] = (u8)((v & 0x0F) | SINGLE);
        else if (typ == LEFT && (m[p + 1] & 0xF0) != RIGHT) m[p] = (u8)((v & 0x0F) | SINGLE);
        else if (typ == RIGHT && (m[(p - 1) & 0xFF] & 0xF0) != LEFT) m[p] = (u8)((v & 0x0F) | SINGLE);
    }
}

// Resolve after a lock; returns virus kills. steps (optional) gets the number of match steps.
static int resolve(u8* m, int* steps = nullptr) {
    int n = 0, s = 0;
    for (;;) {
        while (check_drop(m)) {}
        bool a = check_hor(m, n);
        bool b = check_ver(m, n);
        update_field(m);
        s++;
        if (!(a || b)) { if (steps) *steps = s; return n; }
    }
}

static bool lost(const u8* m) { return m[3] != EMPTY || m[4] != EMPTY; }

// ---------------------------------------------------------------- moves (drm/plan.py)
static int drop_row(const u8* m, int rot, int x) {
    bool v = rot & 1;
    if (x < 0 || x > (v ? 7 : 6)) return -1;
    int last = v ? x : x + 1, lo = std::min(x, 3), hi = std::max(last, 4);
    for (int r = 0; r < 2; r++)
        for (int c = lo; c <= hi; c++)
            if (m[r * 8 + c] != EMPTY) return -1;
    int row = v ? 1 : 0;
    while (row < 15 && m[(row + 1) * 8 + x] == EMPTY && (v || m[(row + 1) * 8 + x + 1] == EMPTY)) row++;
    return row;
}

static void place(u8* m, int rot, int x, int row, int c1, int c2, int* cells) {
    int p = row * 8 + x;
    switch (rot) {
    case 0: m[p] = (u8)(LEFT | c1); m[p + 1] = (u8)(RIGHT | c2); cells[0] = p; cells[1] = p + 1; break;
    case 2: m[p] = (u8)(LEFT | c2); m[p + 1] = (u8)(RIGHT | c1); cells[0] = p; cells[1] = p + 1; break;
    case 1: m[p - 8] = (u8)(TOP | c2); m[p] = (u8)(BOTTOM | c1); cells[0] = p - 8; cells[1] = p; break;
    default: m[p - 8] = (u8)(TOP | c1); m[p] = (u8)(BOTTOM | c2); cells[0] = p - 8; cells[1] = p; break;
    }
}

// Does a run of 4+ pass through cell p? (the board was still before the lock, so only such runs match)
static bool run_at(const u8* m, int p) {
    int c = m[p] & 0x0F, row = p >> 3, col = p & 7, n = 1;
    for (int q = col - 1; q >= 0 && (m[row * 8 + q] & 0x0F) == c; q--) n++;
    for (int q = col + 1; q < 8 && (m[row * 8 + q] & 0x0F) == c; q++) n++;
    if (n >= 4) return true;
    n = 1;
    for (int r = row - 1; r >= 0 && (m[r * 8 + col] & 0x0F) == c; r--) n++;
    for (int r = row + 1; r < 16 && (m[r * 8 + col] & 0x0F) == c; r++) n++;
    return n >= 4;
}

// Lock (rot, x) of pill pid on board m (256 bytes, modified). Returns kills, or -1 if not placeable.
static int play_move(u8* m, int pid, int rot, int x) {
    int row = drop_row(m, rot, x);
    if (row < 0) return -1;
    int cells[2];
    place(m, rot, x, row, pid / 3, pid % 3, cells);
    if (!run_at(m, cells[0]) && !run_at(m, cells[1])) return 0;
    return resolve(m);
}

// Pad rule (tools/pad_rule.py): an NMI can only land in a match call longer than about 24000 cycles, and
// then player 2 must hold that chain's fieldPos_last. pad_ok is true when every chain cleared in a call
// predicted longer than PAD_LONG ends at a value a standard pad can hold (no Left+Right, no Up+Down).
// Cycle model fitted on 308 calls timed by drm/glitch.py (residual sd 582, max 1359).
// scoreMultiplier_table and the bytes after it (drm/board.py MULT, 0 = 256 loops); later kills count as 256.
static const int MULT[30] = {1, 2, 4, 8, 16, 32, 32, 32, 32, 32, 32, 10, 3, 256, 1, 2, 4, 256, 252, 248,
                             244, 242, 241, 240, 241, 242, 244, 248, 252, 256};
static const double PAD_LONG = 20000;
static bool pad_legal(int v) { return (v & 3) != 3 && (v & 12) != 12; }
static bool pad_ok(const u8* board, int pid, int rot, int x) {
    u8 m[256];
    memcpy(m, board, 128);
    memset(m + 128, EMPTY, 128);
    int row = drop_row(m, rot, x), cells[2];
    place(m, rot, x, row, pid / 3, pid % 3, cells);
    int k = 0;
    for (;;) {
        while (check_drop(m)) {}
        bool any = false;
        for (int r = 0; r < 2; r++) {
            int ends[40] = {0}, n = 0;
            bool hit = r == 0 ? check_hor(m, n, ends) : check_ver(m, n, ends);
            any = any || hit;
            double sm = 0;
            for (int i = k; i < k + n; i++) sm += i < 30 ? MULT[i] : 256;
            double cyc = 5854.4 + 93.8 * sm + 153.8 * n + 541.9 * ends[0];
            k += n;
            if (cyc > PAD_LONG)
                for (int i = 1; i <= ends[0]; i++) if (!pad_legal(ends[i])) return false;
        }
        update_field(m);
        if (!any) return true;
    }
}

static int nrots(int pid) { return pid / 3 == pid % 3 ? 2 : 4; }

// Best kills the pill pid can get from board m.
static int best_kills(const u8* m, int pid) {
    int best = 0;
    u8 t[256];
    for (int rot = 0; rot < nrots(pid); rot++)
        for (int x = 0; x < 8; x++) {
            int row = drop_row(m, rot, x);
            if (row < 0) continue;
            int cells[2];
            memcpy(t, m, 128);
            place(t, rot, x, row, pid / 3, pid % 3, cells);
            if (!run_at(t, cells[0]) && !run_at(t, cells[1])) continue;
            memset(t + 128, EMPTY, 128);
            int k = resolve(t);
            if (k > best) best = k;
        }
    return best;
}

// ---------------------------------------------------------------- heuristics
static std::vector<std::vector<int>> WINDOWS;
static void init_windows() {
    for (int r = 0; r < 16; r++)
        for (int c = 0; c < 8; c++) {
            if (c <= 4) WINDOWS.push_back({r * 8 + c, r * 8 + c + 1, r * 8 + c + 2, r * 8 + c + 3});
            if (r <= 12) WINDOWS.push_back({r * 8 + c, (r + 1) * 8 + c, (r + 2) * 8 + c, (r + 3) * 8 + c});
        }
}

// drm/plan.py setup_value: one-colour 4-cell lines holding a virus score (cells filled)^2
static int setup_value(const u8* m) {
    int v = 0;
    for (auto& w : WINDOWS) {
        int col = -1, n = 0;
        bool vir = false, bad = false;
        for (int p : w) {
            u8 x = m[p];
            if (x == EMPTY) continue;
            int c = x & 0x0F;
            if (col < 0) col = c;
            else if (c != col) { bad = true; break; }
            n++;
            vir |= (x & 0xF0) == VIRUS;
        }
        if (!bad && vir && n >= 2) v += n * n;
    }
    return v;
}

static int top_cells(const u8* m, int rows) {
    int n = 0;
    for (int p = 0; p < rows * 8; p++) n += m[p] != EMPTY;
    return n;
}

static int viruses(const u8* m) {
    int n = 0;
    for (int p = 0; p < 128; p++) n += (m[p] & 0xF0) == VIRUS;
    return n;
}

// ---------------------------------------------------------------- search
struct Node { int parent; u8 rot, x; };
struct State { u8 m[128]; double v; int node; int waste; };

static uint64_t hash128(const u8* m) {
    uint64_t h = 1469598103934665603ULL;
    for (int i = 0; i < 128; i++) { h ^= m[i]; h *= 1099511628211ULL; }
    return h;
}

struct Args {
    std::unordered_map<std::string, std::string> kv;
    double get(const char* k, double d) const { auto it = kv.find(k); return it == kv.end() ? d : atof(it->second.c_str()); }
    std::string str(const char* k, const char* d) const { auto it = kv.find(k); return it == kv.end() ? d : it->second; }
};

static void search(const Args& a) {
    int level = (int)a.get("level", 10), n0 = (int)a.get("n0", 1), n1 = (int)a.get("n1", n0 + 1);
    int depth = (int)a.get("depth", 30), beam = (int)a.get("beam", 200), first = (int)a.get("first", 1);
    int minrec = (int)a.get("min", 6), per = (int)a.get("per", 3), pad = (int)a.get("pad", 0);
    double wlook = a.get("look", 1.0), wany = a.get("any", 0.0), wshape = a.get("shape", 0.05);
    double wwaste = a.get("waste", 2.0), wheight = a.get("height", 1.0);
    for (int n = n0; n < n1; n++) {
        auto t0 = std::chrono::steady_clock::now();
        Level L;
        generate(rng_at(n), level, L);
        std::vector<std::vector<Node>> layers;
        std::vector<State> states(1);
        memcpy(states[0].m, L.field, 128);
        states[0].v = 0; states[0].node = -1; states[0].waste = 0;
        int best = 0;
        std::vector<int> count(256, 0);
        int nvir = viruses(L.field);
        for (int d = 0; d < depth && !states.empty(); d++) {
            int pid = L.reserve[(first + d) % 128], nxt = L.reserve[(first + d + 1) % 128];
            std::vector<Node> layer;
            std::vector<State> kids;
            std::unordered_map<uint64_t, int> seen;
            kids.reserve(states.size() * 16);
            // expand every state in parallel (moves + heuristics), then merge serially in state order
            struct Kid { u8 m[128]; u8 rot, x; int k; double v; };
            std::vector<std::vector<Kid>> out(states.size());
#pragma omp parallel for schedule(dynamic, 16)
            for (int si = 0; si < (int)states.size(); si++) {
                u8 t[256];
                for (int rot = 0; rot < nrots(pid); rot++)
                    for (int x = 0; x < 8; x++) {
                        memcpy(t, states[si].m, 128);
                        memset(t + 128, EMPTY, 128);
                        int k = play_move(t, pid, rot, x);
                        if (k < 0 || lost(t)) continue;
                        Kid c;
                        memcpy(c.m, t, 128);
                        c.rot = (u8)rot; c.x = (u8)x; c.k = k;
                        double v = 0;
                        if (wlook) v += wlook * best_kills(t, nxt);
                        if (wany) { int b = 0; for (int p = 0; p < 9; p++) b = std::max(b, best_kills(t, p)); v += wany * b; }
                        if (wshape) v += wshape * setup_value(t);
                        c.v = v - wheight * top_cells(t, 5);
                        out[si].push_back(c);
                    }
            }
            for (int si = 0; si < (int)states.size(); si++) {
                const State& s = states[si];
                for (const Kid& c0 : out[si]) {
                        int k = c0.k, rot = c0.rot, x = c0.x;
                        if (k >= minrec && k >= best - 2 && count[k] < per && (!pad || pad_ok(s.m, pid, rot, x))) {
                            count[k]++;
                            std::vector<std::pair<int, int>> plan{{rot, x}};
                            for (int id = s.node, dd = d - 1; id >= 0; id = layers[dd].at(id).parent, dd--)
                                plan.push_back({layers[dd][id].rot, layers[dd][id].x});
                            std::reverse(plan.begin(), plan.end());
                            printf("{\"n\":%d,\"level\":%d,\"kills\":%d,\"trigger\":%d,\"viruses\":%d,\"waste\":%d,\"plan\":\"",
                                   n, level, k, d, nvir, s.waste);
                            for (size_t i = 0; i < plan.size(); i++) printf("%s%d,%d", i ? " " : "", plan[i].first, plan[i].second);
                            printf("\"}\n");
                            fflush(stdout);
                        }
                        if (k > best) best = k;
                        uint64_t h = hash128(c0.m);
                        int waste = s.waste + k;
                        double v = c0.v - wwaste * waste;
                        auto it = seen.find(h);
                        if (it != seen.end()) {
                            if (kids[it->second].v >= v) continue;
                            State& c = kids[it->second];
                            c.v = v; c.waste = waste;
                            layer[c.node] = {s.node, (u8)rot, (u8)x};
                            continue;
                        }
                        State c;
                        memcpy(c.m, c0.m, 128);
                        c.v = v; c.waste = waste; c.node = (int)layer.size();
                        layer.push_back({s.node, (u8)rot, (u8)x});
                        seen[h] = (int)kids.size();
                        kids.push_back(c);
                }
            }
            if ((int)kids.size() > beam) {
                std::nth_element(kids.begin(), kids.begin() + beam, kids.end(), [](const State& p, const State& q) { return p.v > q.v; });
                kids.resize(beam);
            }
            layers.push_back(std::move(layer));
            states.swap(kids);
        }
        double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        fprintf(stderr, "n %d level %d: best %d (%.1fs)\n", n, level, best, secs);
        printf("{\"n\":%d,\"level\":%d,\"done\":1,\"best\":%d}\n", n, level, best);
        fflush(stdout);
    }
}

static std::string hex(const u8* m, int n) {
    static const char* d = "0123456789ABCDEF";
    std::string s;
    for (int i = 0; i < n; i++) { s += d[m[i] >> 4]; s += d[m[i] & 15]; }
    return s;
}

int main(int argc, char** argv) {
    init_windows();
    if (argc < 2) { fprintf(stderr, "usage: dm version|resolve|play|search key=value...\n"); return 2; }
    Args a;
    for (int i = 2; i < argc; i++) {
        const char* e = strchr(argv[i], '=');
        if (e) a.kv[std::string(argv[i], e - argv[i])] = e + 1;
    }
    std::string mode = argv[1];
    if (mode == "version") {
        printf("%s\n", DM_VERSION);
    } else if (mode == "resolve") {
        char line[1024];
        while (fgets(line, sizeof line, stdin)) {
            if (strlen(line) < 512) continue;
            u8 m[256];
            for (int i = 0; i < 256; i++) { unsigned v; sscanf(line + 2 * i, "%2x", &v); m[i] = (u8)v; }
            int k = resolve(m);
            printf("%d %s\n", k, hex(m, 256).c_str());
        }
    } else if (mode == "play") {
        int n = (int)a.get("n", 1), level = (int)a.get("level", 0), first = (int)a.get("first", 1);
        Level L;
        generate(rng_at(n), level, L);
        u8 m[256];
        memset(m, EMPTY, 256);
        memcpy(m, L.field, 128);
        printf("field %s\nreserve %s\n", hex(L.field, 128).c_str(), hex(L.reserve, 128).c_str());
        std::string plan = a.str("plan", "");
        int i = 0, r, x, off = 0, used;
        while (sscanf(plan.c_str() + off, " %d,%d%n", &r, &x, &used) == 2) {
            off += used;
            int k = play_move(m, L.reserve[(first + i) % 128], r, x);
            printf("pill %d kills %d after %s\n", i, k, hex(m, 128).c_str());
            if (k < 0) return 1;
            i++;
        }
    } else if (mode == "search") {
        search(a);
    }
    return 0;
}
