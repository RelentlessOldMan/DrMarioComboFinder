local done = false
emu.addEventCallback(function()
  if done then return end
  done = true
  local s = emu.getState()
  local keys = {}
  for k, v in pairs(s) do if string.find(k, "cpu") or string.find(k, "ppu.scan") or string.find(k, "ppu.cycle") or string.find(k, "frameCount") then keys[#keys + 1] = k .. "=" .. tostring(v) end end
  table.sort(keys)
  print(table.concat(keys, "\n"))
  emu.stop(0)
end, emu.eventType.endFrame)
