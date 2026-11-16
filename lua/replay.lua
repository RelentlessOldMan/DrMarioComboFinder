-- Replay an input log from lua/play_plan.lua from power-on, optionally dumping every frame as raw
-- 256x240 BGRA for ffmpeg (tools/make_video.ps1). Frame numbering matches play_plan.lua: the counter
-- counts finished frames, and the log line for counter value f is applied at that frame's input poll.
-- Env: DRM_INPUTS, DRM_RAW (optional raw video output), DRM_TAIL (frames to keep running after the log
--      ends, default 180), DRM_OUT (optional: final RAM summary).

local M = emu.memType.nesDebug
local log, last = {}, 0
for line in io.lines(os.getenv("DRM_INPUTS")) do
  local f, p1, p2 = string.match(line, "^(%d+) (%x+) (%x+)")
  if f then log[tonumber(f)] = { tonumber(p1, 16), tonumber(p2, 16) }; last = math.max(last, tonumber(f)) end
end
local tail = tonumber(os.getenv("DRM_TAIL") or "180")
local raw = os.getenv("DRM_RAW") and assert(io.open(os.getenv("DRM_RAW"), "wb"))

local NAMES = { [0x80] = "a", [0x40] = "b", [0x20] = "select", [0x10] = "start", [0x08] = "up", [0x04] = "down", [0x02] = "left", [0x01] = "right" }
local function pad(m)
  local t = {}
  for bit, name in pairs(NAMES) do t[name] = (m & bit) ~= 0 end
  return t
end

local ROW = "<" .. string.rep("I4", 256)
local frame = 0
emu.addEventCallback(function()
  local e = log[frame]
  if e then
    emu.setInput(pad(e[1]), 0)
    emu.setInput(pad(e[2]), 0, 1)
  end
end, emu.eventType.inputPolled)

emu.addEventCallback(function()
  frame = frame + 1
  if raw then
    local buf = emu.getScreenBuffer()
    local parts = {}
    for i = 1, #buf, 256 do parts[#parts + 1] = string.pack(ROW, table.unpack(buf, i, i + 255)) end
    raw:write(table.concat(parts))
  end
  if frame > last + tail then
    if raw then raw:close() end
    local o = os.getenv("DRM_OUT")
    if o then
      local f = assert(io.open(o, "w"))
      local s = 0
      for i = 5, 0, -1 do s = s * 10 + emu.read(0x0729 + i, M) end
      f:write(string.format('{"frames":%d,"score":%d}\n', frame, s * 10)); f:close()
    end
    emu.stop(0)
  end
end, emu.eventType.endFrame)
