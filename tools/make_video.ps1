# Replay an input log in Mesen (lua/replay.lua) and encode the frames to MP4 (no audio).
# Usage: tools\make_video.ps1 <inputs file> <out.mp4>
param([string]$Inputs, [string]$Out)
$root = Split-Path $PSScriptRoot -Parent
$Out = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Out))
$raw = [IO.Path]::ChangeExtension($Out, ".raw")
$env:DRM_INPUTS = (Resolve-Path $Inputs).Path; $env:DRM_RAW = $raw; $env:DRM_OUT = [IO.Path]::ChangeExtension($Out, ".json")
$p = Start-Process "$root\mesen\Mesen.exe" -ArgumentList "--testRunner", "--timeout=1800", "$root\lua\replay.lua", "$root\drmario.nes" -PassThru -NoNewWindow
$p.WaitForExit()
# NTSC NES: 60.0988 frames per second; scale 3x with nearest-neighbour so pixels stay sharp
& C:\Utils\ffmpeg.exe -y -loglevel error -f rawvideo -pixel_format bgra -video_size 256x240 -framerate 60.0988 -i $raw `
  -vf "scale=768:720:flags=neighbor,format=yuv420p" -c:v libx264 -crf 16 $Out
if ($?) { Remove-Item $raw }
if (Test-Path $env:DRM_OUT) { Get-Content $env:DRM_OUT } else { Write-Error "replay did not finish: $Out is incomplete"; exit 1 }
