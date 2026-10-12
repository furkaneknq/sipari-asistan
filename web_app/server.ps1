# =====================================================================
# Sipariş Takip Sistemi - Hafif Yerel Web Sunucusu & Ters Proxy
# Zero Dependency: Node.js veya Python gerektirmeden çalışır.
# =====================================================================

param([int]$Port = 5050)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

$mimeTypes = @{
    ".html" = "text/html; charset=utf-8"
    ".htm"  = "text/html; charset=utf-8"
    ".css"  = "text/css; charset=utf-8"
    ".js"   = "application/javascript; charset=utf-8"
    ".json" = "application/json; charset=utf-8"
    ".png"  = "image/png"
    ".jpg"  = "image/jpeg"
    ".jpeg" = "image/jpeg"
    ".svg"  = "image/svg+xml"
    ".ico"  = "image/x-icon"
}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Prefixes.Add("http://127.0.0.1:$Port/")

try {
    $listener.Start()
} catch {
    Write-Host "Port $Port dolu olabilir veya yetki gerekiyor. Hata: $_" -ForegroundColor Red
    exit 1
}

$url = "http://localhost:$Port/"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " 🚀 Sipariş Takip Sistemi Web Sunucusu & Proxy Başlatıldı!" -ForegroundColor Green
Write-Host " Adres: $url" -ForegroundColor Yellow
Write-Host " Tarayıcı açılıyor... (Durdurmak için Ctrl+C tuşlayın)" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Cyan

Start-Process $url

$supabaseBase = "https://xgvlgmikxchpttydtelb.supabase.co"

while ($listener.IsListening) {
    try {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response

        # CORS Başlıkları
        $response.Headers.Add("Access-Control-Allow-Origin", "*")
        $response.Headers.Add("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        $response.Headers.Add("Access-Control-Allow-Headers", "apikey, authorization, content-type, prefer, range, x-client-info")

        if ($request.HttpMethod -eq "OPTIONS") {
            $response.StatusCode = 200
            $response.Close()
            continue
        }

        # 1. Supabase Ters Proxy İsteği (/supabase-proxy/...)
        if ($request.Url.LocalPath.StartsWith("/supabase-proxy/")) {
            $subPath = $request.Url.PathAndQuery.Substring(16)
            $targetUrl = "$supabaseBase/$subPath"

            try {
                $targetReq = [System.Net.HttpWebRequest]::Create($targetUrl)
                $targetReq.Method = $request.HttpMethod
                $targetReq.UserAgent = "OrderTrackingDesktopBridge/1.0"
                $targetReq.Timeout = 15000

                foreach ($headerKey in $request.Headers.AllKeys) {
                    if ($headerKey -in @("apikey", "Authorization", "Prefer", "Range")) {
                        $targetReq.Headers.Add($headerKey, $request.Headers[$headerKey])
                    } elseif ($headerKey -eq "Content-Type") {
                        $targetReq.ContentType = $request.ContentType
                    }
                }

                if ($request.HasEntityBody) {
                    $bodyBytes = [System.IO.File]::ReadAllBytes("")
                    $reqStream = $request.InputStream
                    $targetStream = $targetReq.GetRequestStream()
                    $reqStream.CopyTo($targetStream)
                    $targetStream.Close()
                }

                $targetRes = $targetReq.GetResponse()
                $response.StatusCode = [int]$targetRes.StatusCode
                $response.ContentType = $targetRes.ContentType

                $resStream = $targetRes.GetResponseStream()
                $resStream.CopyTo($response.OutputStream)
                $resStream.Close()
                $targetRes.Close()
            } catch [System.Net.WebException] {
                $webEx = $_.Exception
                if ($webEx.Response) {
                    $errRes = [System.Net.HttpWebResponse]$webEx.Response
                    $response.StatusCode = [int]$errRes.StatusCode
                    $response.ContentType = $errRes.ContentType
                    $errStream = $errRes.GetResponseStream()
                    $errStream.CopyTo($response.OutputStream)
                    $errStream.Close()
                } else {
                    $response.StatusCode = 500
                    $errBytes = [System.Text.Encoding]::UTF8.GetBytes($_.Exception.Message)
                    $response.OutputStream.Write($errBytes, 0, $errBytes.Length)
                }
            }

            $response.Close()
            continue
        }

        # 2. Statik Dosya Sunumu
        $path = $request.Url.LocalPath.TrimStart('/')
        if ([string]::IsNullOrWhiteSpace($path)) {
            $path = "index.html"
        }

        $filePath = Join-Path $scriptDir $path

        if (Test-Path $filePath -PathType Leaf) {
            $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
            $mime = if ($mimeTypes.ContainsKey($ext)) { $mimeTypes[$ext] } else { "application/octet-stream" }

            $bytes = [System.IO.File]::ReadAllBytes($filePath)
            $response.ContentType = $mime
            $response.ContentLength64 = $bytes.Length
            $response.OutputStream.Write($bytes, 0, $bytes.Length)
        } else {
            $response.StatusCode = 404
            $msg = [System.Text.Encoding]::UTF8.GetBytes("404 - Dosya Bulunamadı: $path")
            $response.OutputStream.Write($msg, 0, $msg.Length)
        }

        $response.Close()
    } catch {
        # İstek kesintisi vb.
    }
}
