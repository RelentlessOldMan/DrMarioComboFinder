-- Rules check: for each trial, write a random board into the P1 field, put the falling pill above a
-- random column with a random rotation and colours, hold Down, and record the field at lock and after
-- the game has resolved drops/matches, plus the score change. tools/check_rules.py replays the same
-- locks through drm/board.py.
-- Env: DRM_TRIALS (count), DRM_SEED (Lua RNG seed), DRM_OUT (jsonl).

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

emu.addMemoryCallback(function(addr, value)
  if phase == "falling" and value == 1 then
    lock_field = hexs(0x0400, 128); lock_score = score(); phase = "resolving"
  elseif phase == "resolving" and value == 2 then
    out:write(string.format('{"trial":%d,"speed":%d,"start":"%s","lock":"%s","final":"%s","beyond":"%s","dscore":%d,"mult":%d,"rot":%d}\n',
      trial, rd(0x8B), rec.start, lock_field, hexs(0x0400, 128), hexs(0x0480, 128), score() - lock_score, rd(0xAD), rec.rot))
    out:flush()
    phase = "next"
  end
end, emu.callbackType.write, 0x97)

local hold = {}
emu.addEventCallback(function()
  frame = frame + 1
  if phase == "boot" then
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

emu.addEventCallback(function()
  if next(hold) then emu.setInput(hold, 0) end
end, emu.eventType.inputPolled)
emu.addEventCallback(function() if phase ~= "falling" then hold = {} end end, emu.eventType.startFrame)
