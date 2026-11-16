-- Smoke test: run 300 frames, report RNG, mode and frame counter, then exit.
local frames = 0
emu.addEventCallback(function()
  frames = frames + 1
  if frames == 300 then
    local rng = emu.read(0x17, emu.memType.nesDebug) * 256 + emu.read(0x18, emu.memType.nesDebug)
    print(string.format("frames=%d rng=%04X mode=%d fc=%d", frames, rng,
      emu.read(0x46, emu.memType.nesDebug), emu.read(0x43, emu.memType.nesDebug)))
    emu.stop(0)
  end
end, emu.eventType.endFrame)
