-- Timing probe (from rules_check.lua): also logs CPU cycles of NMIs, match steps, clear loops and
-- scoreIncrease calls, and starts the kill counter at a random k0 so heavy multipliers happen.
-- If an NMI lands inside a clear loop it is logged and $49 is put back so the run continues.
-- Rules check: for each trial, write a random board into the P1 field, put the falling pill above a
-- random column with a random rotation and colours, hold Down, and record the field at lock and after
-- the game has resolved drops/matches, plus the score change. tools/check_rules.py replays the same
-- locks through drm/board.py.
-- Env: DRM_MUSIC (0 fever, 1 chill, 2 off; optional), DRM_TRIALS (count), DRM_SEED (Lua RNG seed), DRM_OUT (jsonl).

local M = emu.memType.nesDebug
local function rd(a) return emu.read(a, M) end
local function wr(a, v) emu.write(a, v, M) end

local trials = tonumber(os.getenv("DRM_TRIALS") or "50")
math.randomseed(tonumber(os.getenv("DRM_SEED") or "1"))
local out = assert(io.open(os.getenv("DRM_OUT") or "rules_check.jsonl", "w"))

local function hexs(a, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%02X", rd(a + i)) end
  return table.concat(t)
end
local function score()
  local s = 0
  for i = 5, 0, -1 do s = s * 10 + rd(0x0729 + i) end
  return s * 10
end

-- random board: rows 4..15 hold viruses, single halves and pill pairs, often floating
local function random_board()
  local f = {}
  for i = 0, 127 do f[i] = 0xFF end
  local density = 0.25 + math.random() * 0.5
  for row = 4, 15 do
    for col = 0, 7 do
      local p = row * 8 + col
      if f[p] == 0xFF and math.random() < density then
        local k, c = math.random(), math.random(0, 2)
        if k < 0.45 then f[p] = 0xD0 | c
        elseif k < 0.7 then f[p] = 0x80 | c
        elseif k < 0.85 and col < 7 and f[p + 1] == 0xFF then
          f[p] = 0x60 | c; f[p + 1] = 0x70 | math.random(0, 2)
        elseif row > 4 and f[p - 8] == 0xFF then
          f[p - 8] = 0x40 | c; f[p] = 0x50 | math.random(0, 2)
        end
      end
    end
  end
  return f
end

local trial, phase, wait, lock_field, lock_score, rec = 0, "boot", 0, nil, 0, nil
local frame, last_press = 0, -100

local ev, armed, armed_val, k0, glitched, dumps = {}, false, 0, 0, 0, {}
local function dump() dumps[#dumps + 1] = hexs(0x0000, 0x800) end
local function cyc() return emu.getState()["cpu.cycleCount"] end
local function log(t, x) ev[#ev + 1] = t .. cyc() .. (x and (":" .. x) or "") end
local function on(addr, f) emu.addMemoryCallback(f, emu.callbackType.exec, addr) end
on(0x8005, function() if phase == "resolving" then log("N", armed and "armed" or nil); if armed then glitched = glitched + 1 end end end)
on(0x91FB, function()
  if phase == "resolving" then
    if k0 < 0 then k0 = math.random(0, 40); emu.write(0xAD, k0, M) end
    log("H"); dump()
  end
end)
on(0x92DA, function() if phase == "resolving" then log("h") end end)
on(0x9469, function() if phase == "resolving" then log("V"); dump() end end)
on(0x952F, function() if phase == "resolving" then log("v") end end)
on(0x925F, function() if phase == "resolving" then armed = true; log("A") end end)
on(0x94C5, function() if phase == "resolving" then armed = true; log("A") end end)
on(0x9261, function() armed_val = emu.read(0x49, M) end)
on(0x94C7, function() armed_val = emu.read(0x49, M) end)
-- DRM_P2FIX: no repair; instead player 2 holds the buttons whose bits equal fieldPos_last while a clear
-- loop runs, so the NMI's getInputs writes the same value back. A changed $49 is logged as "B" (broken).
local p2fix = os.getenv("DRM_P2FIX")
local function check49()
  if armed and emu.read(0x49, M) ~= armed_val then
    if p2fix then log("B", string.format("%02X>%02X", armed_val, emu.read(0x49, M))) end
    emu.write(0x49, armed_val, M)
  end
end
on(0x929C, check49)
on(0x94FF, check49)
on(0x92A2, check49)
on(0x9505, check49)
on(0x92A0, function() if phase == "resolving" then armed = false; log("D") end end)
on(0x9503, function() if phase == "resolving" then armed = false; log("D") end end)
on(0x8FF4, function() if phase == "resolving" then log("S", emu.read(0xAD, M)) end end)
on(0x901B, function() if phase == "resolving" then log("s") end end)
local tail = false
-- metaspriteUpdate keeps its data pointer in tmp47/48; put tmp48 back if an NMI overwrote it (logged X)
local ms_hi = nil
on(0x8906, function() ms_hi = rd(0x48) end)
on(0x890A, function() if ms_hi and rd(0x48) ~= ms_hi then wr(0x48, ms_hi); if phase == "resolving" then log("X") end end end)
on(0x893A, function() ms_hi = nil end)
on(0x92DA, function() tail = true end)
on(0x952F, function() tail = true end)
on(0xB662, function() if tail then tail = false; if phase == "resolving" then log("W") end end end)
on(0x88F6, function() if phase == "resolving" and tail then log("M") end end)
on(0x893A, function() if phase == "resolving" and tail then log("m") end end)


emu.addMemoryCallback(function(addr, value)
  if phase == "falling" and value == 1 then
    lock_field = hexs(0x0400, 128); lock_score = score(); phase = "resolving"; ev = {}; k0 = -1; glitched = 0; dumps = {}
  elseif phase == "resolving" and value == 2 then
    out:write(string.format('{"trial":%d,"speed":%d,"start":"%s","lock":"%s","final":"%s","beyond":"%s","dscore":%d,"mult":%d,"rot":%d,"k0":%d,"glitched":%d,"ev":"%s","dumps":["%s"]}\n',
      trial, rd(0x8B), rec.start, lock_field, hexs(0x0400, 128), hexs(0x0480, 128), score() - lock_score, rd(0xAD), rec.rot,
      math.max(k0, 0), glitched, table.concat(ev, " "), table.concat(dumps, '","')))
    out:flush()
    phase = "next"
  end
end, emu.callbackType.write, 0x97)

local hold = {}
emu.addEventCallback(function()
  frame = frame + 1
  if phase == "resolving" then stuck = (stuck or 0) + 1 else stuck = 0 end
  if stuck == 1200 then
    local f = assert(io.open((os.getenv("DRM_OUT") or "x") .. ".stuck.hex", "w"))
    f:write(hexs(0x0000, 0x800), "\n", rec.start, "\n", lock_field, "\n", table.concat(ev, " "), "\n"); f:close()
    out:close(); emu.stop(1); return
  end
  if os.getenv("DRM_DEBUG") and frame % 300 == 0 then print(string.format("f%d trial %d phase %s mode %d act %d rng %02X%02X lvl %d pc %04X step %d ad %d 49 %02X 59 %02X 5A %02X", frame, trial, phase, rd(0x46), rd(0x0317), rd(0x17), rd(0x18), rd(0x0316), emu.getState()["cpu.pc"], rd(0x87), rd(0xAD), rd(0x49), rd(0x59), rd(0x5A))) end
  if phase == "boot" then
    local mus = os.getenv("DRM_MUSIC")
    if mus and rd(0x46) <= 1 then wr(0x0731, tonumber(mus)) end
    -- title -> options -> start level (settings as left by the previous run)
    if rd(0x46) <= 1 and frame - last_press >= 20 then hold = { start = true }; last_press = frame end
    if rd(0x46) == 4 and rd(0x0317) == 0 then phase = "next" end
  elseif phase == "next" and rd(0x0317) == 0 then
    trial = trial + 1
    if trial > trials then out:close(); emu.stop(0); return end
    local f = random_board()
    local t = {}
    for i = 0, 127 do wr(0x0400 + i, f[i]); t[#t + 1] = string.format("%02X", f[i]) end
    local rot = math.random(0, 3)
    local x = math.random(0, (rot % 2 == 1) and 7 or 6)
    wr(0x0305, x); wr(0x0306, 12); wr(0x0325, rot)
    wr(0x0301, math.random(0, 2)); wr(0x0302, math.random(0, 2))
    wr(0x0324, 0x99)  -- virus count (BCD) high so the level never ends
    rec = { start = table.concat(t), rot = rot }
    phase = "falling"
  end
  if phase == "falling" or phase == "resolving" then hold = { down = true } end
end, emu.eventType.endFrame)

local bits = { "right", "left", "down", "up", "start", "select", "b", "a" }
emu.addEventCallback(function()
  if next(hold) then emu.setInput(hold, 0) end
  if p2fix and armed then
    local p2 = {}
    for i, name in ipairs(bits) do p2[name] = (armed_val >> (i - 1)) & 1 == 1 end
    emu.setInput(p2, 0, 1)  -- Mesen runs this ROM as a Famicom: both pads are subports of port 0
  end
end, emu.eventType.inputPolled)
emu.addEventCallback(function() if phase ~= "falling" then hold = {} end end, emu.eventType.startFrame)
