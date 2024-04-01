# 设置源文件路径
$source = "C:\path\to\your\large\file"
# 设置目标文件夹路径
$destination = "C:\path\to\destination\folder"
# 设置每个分割文件的大小（以字节为单位）
$chunkSize = 100MB

# 创建目标文件夹，如果不存在的话
if (-not (Test-Path -Path $destination)) {
    New-Item -ItemType directory -Path $destination
}

# 分割文件
$buffer = New-Object byte[] $chunkSize
$stream = [System.IO.File]::OpenRead($source)
try {
    $chunkNum = 0
    while ($stream.Position -lt $stream.Length) {
        $readLength = $stream.Read($buffer, 0, $buffer.Length)
        $targetFilePath = [System.IO.Path]::Combine($destination, "part${chunkNum}.dat")
        [System.IO.File]::WriteAllBytes($targetFilePath, $buffer[0..($readLength-1)])
        $chunkNum++
    }
} finally {
    $stream.Close()
}
