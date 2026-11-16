-- Start levels at chosen RNG indices by timing START on the options screen, then dump what was generated.
-- Env: DRM_NS = comma list of indices N or N@level (RNG = $8988 stepped N times when START is read),
--      DRM_LEVEL (0-20), DRM_OUT = output file (one JSON object per line).
-- Each run ends with a soft reset, which re-seeds the RNG and keeps the level/speed settings.

local M = emu.memType.nesDebug
local function rd(a) return emu.read(a, M) end
local function rng() return rd(0x17) * 256 + rd(0x18) end

local function step(r)
  local bit = ((r >> 9) ~ (r >> 1)) & 1
  return (r >> 1) | (bit << 15)
end
local index, r = {}, 0x8988
for i = 0, 32766 do index[r] = i; r = step(r) end

-- entries are "N" or "N@level"; a bare N uses DRM_LEVEL
local ns, levels = {}, {}
local default_level = tonumber(os.getenv("DRM_LEVEL") or "0")
for s in string.gmatch(os.getenv("DRM_NS") or "1", "[^,]+") do
  local n, l = string.match(s, "^(%d+)@(%d+)$")
  ns[#ns + 1] = tonumber(n or s); levels[#ns] = tonumber(l) or default_level
end
local out = assert(io.open(os.getenv("DRM_OUT") or "pick_seed.jsonl", "w"))

local run, phase, frame, press, last_press, mode_log = 1, "title", 0, {}, -100, {}

local function hexs(a, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%02X", rd(a + i)) end
  return table.concat(t)
end

emu.addMemoryCallback(function(addr, value)
  mode_log[#mode_log + 1] = string.format("%d:%04X", value, rng())
end, emu.callbackType.write, 0x46)

emu.addEventCallback(function()
  frame = frame + 1
  local N, want_level = ns[run], levels[run]
  if phase == "title" then
    -- tap START on the title (mode 0, freshly seeded) until the options menu (mode 1) is up
    if rd(0x46) == 1 and index[rng()] then
      phase = "options"
    elseif rd(0x46) == 0 and rng() == 0x8988 and frame - last_press >= 20 then
      press = { start = true }; last_press = frame
    end
  end
  if phase == "options" then
    local lvl = rd(0x0316)
    if lvl < want_level and frame % 2 == 0 then press = { right = true }
    elseif lvl > want_level and frame % 2 == 0 then press = { left = true } end
    -- the next options-loop pass steps the RNG then reads START
    if index[rng()] == N - 1 then
      if lvl ~= want_level then
        out:write(string.format('{"n":%d,"error":"level not set in time (%d)"}\n', N, lvl))
        phase = "next"
      else
        press = { start = true }; phase = "started"
      end
    elseif index[rng()] >= N then
      out:write(string.format('{"n":%d,"error":"missed (at %d)"}\n', N, index[rng()]))
      phase = "next"
    end
  elseif phase == "started" and rd(0x46) == 4 then
    phase = "settle"; frame = 0
  elseif phase == "settle" and frame >= 2 then
    out:write(string.format(
      '{"n":%d,"level":%d,"speed":%d,"rng":"%04X","field":"%s","beyond":"%s","reserve":"%s","cur":"%02X%02X","next":"%02X%02X","reserve_idx":%d,"modes":"%s"}\n',
      N, rd(0x0316), rd(0x030B), rng(), hexs(0x0400, 128), hexs(0x0480, 16), hexs(0x0780, 128),
      rd(0x0301), rd(0x0302), rd(0x031A), rd(0x031B), rd(0x0327), table.concat(mode_log, " ")))
    out:flush()
    phase = "next"
  end
  if phase == "next" then
    run = run + 1
    if run > #ns then out:close(); emu.stop(0); return end
    phase, frame, last_press, mode_log = "title", 0, -100, {}
    emu.reset()
  end
end, emu.eventType.endFrame)

emu.addEventCallback(function()
  if next(press) then emu.setInput(press, 0) end
end, emu.eventType.inputPolled)

-- clear the press once the frame's NMI has read it
emu.addEventCallback(function() press = {} end, emu.eventType.startFrame)
