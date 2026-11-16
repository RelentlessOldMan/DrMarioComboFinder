-- Play a placement plan: start the level at RNG index N (as pick_seed.lua does) with the chosen level,
-- speed and music, then for each pill rotate and move it to the planned (rotation, x) and hold Down.
-- Every frame's P1/P2 input is logged so lua/replay.lua can play the run back exactly (for video).
-- Steering reads the pill's own RAM, so the plan only says where each pill goes, not how.
-- Env: DRM_N, DRM_LEVEL, DRM_SPEED (0-2, default 1), DRM_MUSIC (0 fever, 1 chill, 2 off; default 0),
--      DRM_P2 (1: player 2 holds fieldPos_last while a clear loop can be interrupted, see RESEARCH.md),
--      DRM_PLAN (file: one "rot x" line per pill), DRM_OUT (jsonl, one line per pill),
--      DRM_INPUTS (input log, "frame p1 p2" hex per line).
-- Glitches are not repaired, only reported per pill: g1 = $49 changed inside a clear loop, g2 = the
-- metasprite pointer (tmp48) changed inside metaspriteUpdate.

local M = emu.memType.nesDebug
local function rd(a) return emu.read(a, M) end
local function rng() return rd(0x17) * 256 + rd(0x18) end
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

local function step(r)
  local bit = ((r >> 9) ~ (r >> 1)) & 1
  return (r >> 1) | (bit << 15)
end
local index, r = {}, 0x8988
for i = 0, 32766 do index[r] = i; r = step(r) end

local N = tonumber(os.getenv("DRM_N") or "1")
local want = { tonumber(os.getenv("DRM_LEVEL") or "0"), tonumber(os.getenv("DRM_SPEED") or "1"),
               tonumber(os.getenv("DRM_MUSIC") or "0") }
local p2fix = os.getenv("DRM_P2") == "1"
local plan = {}
for line in io.lines(os.getenv("DRM_PLAN")) do
  local rot, x = string.match(line, "^%s*(%d+)%s+(%d+)")
  if rot then plan[#plan + 1] = { rot = tonumber(rot), x = tonumber(x) } end
end
local out = assert(io.open(os.getenv("DRM_OUT") or "play.jsonl", "w"))
local inputs = assert(io.open(os.getenv("DRM_INPUTS") or "play.inputs", "w"))

local BITS = { a = 0x80, b = 0x40, select = 0x20, start = 0x10, up = 0x08, down = 0x04, left = 0x02, right = 0x01 }
local function mask(t)
  local m = 0
  for k, v in pairs(t) do if v then m = m | BITS[k] end end
  return m
end
local function pad(m)
  local t = {}
  for k, b in pairs(BITS) do t[k] = (m & b) ~= 0 end
  return t
end

local phase, frame, last_press, press = "title", 0, -100, {}
local pill, pill_count, lock_field, lock_score = 0, nil, nil, 0
local g1, g2, p2frames, p2vals = 0, 0, 0, {}
local function finish(code)
  if phase == "done" then return end
  phase = "done"; out:close(); inputs:close(); emu.stop(code)
end

-- clear-loop tracking (drm/glitch.py _ARM/_DONE): armed from `sta fieldPos_last` to its last read
local armed, armed_val = false, 0
local function on(addr, f) emu.addMemoryCallback(f, emu.callbackType.exec, addr) end
on(0x9261, function() armed, armed_val = true, rd(0x49) end)
on(0x94C7, function() armed, armed_val = true, rd(0x49) end)
local function check49() if armed and rd(0x49) ~= armed_val then g1 = g1 + 1 end end
on(0x929C, check49); on(0x94FF, check49); on(0x92A2, check49); on(0x9505, check49)
on(0x92A4, function() armed = false end)
on(0x9507, function() armed = false end)
local ms_hi
on(0x8906, function() ms_hi = rd(0x48) end)
on(0x890A, function() if ms_hi and rd(0x48) ~= ms_hi then g2 = g2 + 1 end end)

emu.addMemoryCallback(function(addr, value)
  if phase ~= "play" then return end
  if value == 1 and not lock_field then
    lock_field, lock_score = hexs(0x0400, 128), score()
  end
end, emu.callbackType.write, 0x0317)

local function report(final)
  local p = plan[pill]
  out:write(string.format('{"pill":%d,"want_rot":%d,"want_x":%d,"rot":%d,"x":%d,"lock":"%s","after":"%s","dscore":%d,"score":%d,"frame":%d,"g1":%d,"g2":%d,"p2frames":%d,"p2vals":"%s"}\n',
    pill - 1, p.rot, p.x, rd(0x0325), rd(0x0305), lock_field or "", final, score() - lock_score, score(), frame,
    g1, g2, p2frames, table.concat(p2vals, " ")))
  out:flush()
  g1, g2, p2frames, p2vals = 0, 0, 0, {}
end

-- options screen: each section is set with Left/Right, then Down moves to the next ($65 = section)
local function option_value(s)
  if s == 0 then return rd(0x0316) elseif s == 1 then return rd(0x030B) else return rd(0x0731) end
end

emu.addEventCallback(function()
  if phase == "done" then return end
  frame = frame + 1
  if phase == "title" then
    if rd(0x46) == 1 and index[rng()] then
      phase = "options"
    elseif rd(0x46) == 0 and rng() == 0x8988 and frame - last_press >= 20 then
      press = { start = true }; last_press = frame
    end
  end
  if phase == "options" then
    local s = rd(0x65)
    local v = option_value(s)
    local set = true
    for i = 0, 2 do if option_value(i) ~= want[i + 1] then set = false end end
    if frame % 2 == 0 and not set then
      if v < want[s + 1] then press = { right = true }
      elseif v > want[s + 1] then press = { left = true }
      elseif s < 2 then press = { down = true }
      else press = { up = true } end
    end
    if index[rng()] == N - 1 then
      if not set then print("options not set in time"); finish(2); return end
      press = { start = true }; phase = "started"
    elseif index[rng()] >= N then
      print("missed N"); finish(2); return
    end
  elseif phase == "started" and rd(0x46) == 4 then
    phase = "play"
  end
  if phase == "play" then
    if rd(0x46) ~= 4 then print("left level mode at pill " .. pill); finish(0); return end
    if rd(0x0317) == 0 then
      local count = rd(0x0327)
      if count ~= pill_count then
        -- a new pill is in play: report the previous one (its cascade is over)
        if pill > 0 then report(hexs(0x0400, 128)) end
        lock_field = nil
        pill_count = count
        pill = pill + 1
        if pill > #plan then finish(0); return end
      end
      local p = plan[pill]
      local rot, x = rd(0x0325), rd(0x0305)
      if rot == p.rot and x == p.x then
        press = { down = true }
      elseif frame % 2 == 0 then
        -- rotate and move in the same frame (the game does Y, then X, then rotation)
        press = {}
        if rot ~= p.rot then
          if (rot + 1) & 3 == p.rot then press.b = true else press.a = true end
        end
        if x < p.x then press.right = true elseif x > p.x then press.left = true end
      end
    end
  end
end, emu.eventType.endFrame)

emu.addEventCallback(function()
  if phase == "done" then return end
  if next(press) then emu.setInput(press, 0) end
  local p2 = 0
  if p2fix and armed then
    p2 = armed_val
    emu.setInput(pad(p2), 0, 1)  -- Mesen runs this ROM as a Famicom: both pads are subports of port 0
    p2frames = p2frames + 1
    p2vals[#p2vals + 1] = string.format("%02X", p2)
  end
  inputs:write(string.format("%d %02X %02X\n", frame, mask(press), p2))
end, emu.eventType.inputPolled)
emu.addEventCallback(function() press = {} end, emu.eventType.startFrame)
