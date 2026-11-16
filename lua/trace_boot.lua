-- Trace: tap START once at frame 120, log mode ($46) and RNG every frame for 400 frames.
local M = emu.memType.nesDebug
local function rd(a) return emu.read(a, M) end
local out = assert(io.open(os.getenv("DRM_OUT"), "w"))
local frame, t0 = 0, os.clock()
emu.addEventCallback(function()
  frame = frame + 1
  out:write(string.format("%d mode=%d rng=%02X%02X pressed=%02X lvl=%d\n", frame, rd(0x46), rd(0x17), rd(0x18), rd(0xF5), rd(0x0316)))
  if frame == 400 then
    out:write(string.format("cpu secs %.2f\n", os.clock() - t0)); out:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)
emu.addEventCallback(function()
  if frame == 120 then emu.setInput({ start = true }, 0) end
end, emu.eventType.inputPolled)
