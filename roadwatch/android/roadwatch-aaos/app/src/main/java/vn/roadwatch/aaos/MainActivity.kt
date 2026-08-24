package vn.roadwatch.aaos

import android.annotation.SuppressLint
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    companion object {
        private const val TAG = "RoadWatch.MainActivity"
    }
    private val handler = Handler(Looper.getMainLooper())
    private val vehicle: VehicleAdapter = MockVehicleAdapter()
    private lateinit var webView: WebView
    private val roadWatchUrls by lazy {
        listOf(BuildConfig.ROADWATCH_URL, BuildConfig.ROADWATCH_FALLBACK_URL).distinct()
    }
    private var currentUrlIndex = 0

    private val publishTelemetry = object : Runnable {
        override fun run() {
            val payload = vehicle.read().toJson()
            webView.evaluateJavascript(
                "window.dispatchEvent(new CustomEvent('roadwatch-vehicle-telemetry',{detail:$payload}));",
                null,
            )
            handler.postDelayed(this, 500)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        webView = WebView(this).apply {
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                mediaPlaybackRequiresUserGesture = false
                mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                useWideViewPort = true
                loadWithOverviewMode = true
            }
            webViewClient = object : WebViewClient() {
                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    val errorCode = error?.errorCode
                    val description = error?.description
                    val failingUrl = request?.url?.toString()
                    Log.e(TAG, "WebView Error ($errorCode): $description at $failingUrl")

                    if (request?.isForMainFrame == true) {
                        if (currentUrlIndex + 1 < roadWatchUrls.size) {
                            currentUrlIndex += 1
                            val fallback = roadWatchUrls[currentUrlIndex]
                            Toast.makeText(
                                this@MainActivity,
                                "Đang thử kết nối dự phòng: $fallback",
                                Toast.LENGTH_SHORT,
                            ).show()
                            view?.post { view.loadUrl(fallback) }
                        } else {
                            showConnectionError(description?.toString() ?: "Không thể kết nối")
                        }
                    }
                }
            }
            webChromeClient = WebChromeClient()
            Log.d(TAG, "Loading URL: ${roadWatchUrls.first()}")
            loadUrl(roadWatchUrls.first())
        }
        setContentView(webView)
        handler.post(publishTelemetry)
    }

    override fun onDestroy() {
        handler.removeCallbacks(publishTelemetry)
        webView.destroy()
        super.onDestroy()
    }

    private fun showConnectionError(description: String) {
        val retryUrl = roadWatchUrls.first()
        val html = """
            <!doctype html><html lang="vi"><meta name="viewport" content="width=device-width,initial-scale=1">
            <body style="font-family:sans-serif;background:#071b33;color:white;padding:32px">
              <h2>RoadWatch chưa kết nối được backend</h2>
              <p>${description.replace("<", "&lt;").replace(">", "&gt;")}</p>
              <p>Trên Windows, chạy <b>scripts/configure_aaos_emulator.ps1</b>, sau đó khởi động RoadWatch.</p>
              <button style="font-size:20px;padding:12px 20px" onclick="location.href='$retryUrl'">Thử lại</button>
            </body></html>
        """.trimIndent()
        webView.loadDataWithBaseURL(retryUrl, html, "text/html", "UTF-8", null)
    }
}
