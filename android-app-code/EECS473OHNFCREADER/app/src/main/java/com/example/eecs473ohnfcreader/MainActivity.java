package com.example.eecs473ohnfcreader;

import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Typeface;
import android.nfc.NdefMessage;
import android.nfc.NdefRecord;
import android.nfc.NfcAdapter;
import android.os.Bundle;
import android.os.Parcelable;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import java.nio.charset.StandardCharsets;

public class MainActivity extends AppCompatActivity {

    private NfcAdapter nfcAdapter;
    private PendingIntent pendingIntent;
    private IntentFilter[] intentFiltersArray;
    private WebView eecs_oh;
    private AlertDialog nfcDialog;
    boolean readNFC = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        Button reloadButton = findViewById(R.id.reload_button);
        reloadButton.setOnClickListener(v -> {
            if (eecs_oh != null) {
                eecs_oh.reload();
                Toast.makeText(MainActivity.this, "Page Reloaded", Toast.LENGTH_SHORT).show();
            }
        });

        setupWebView();

        nfcAdapter = NfcAdapter.getDefaultAdapter(this);
        if (nfcAdapter == null) {
            TextView textView = findViewById(R.id.nfc_tag_message);
            textView.setText("NFC not supported on this device");
            return;
        }

        Intent intent = new Intent(this, getClass()).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        pendingIntent = PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_MUTABLE);

        IntentFilter ndefFilter = new IntentFilter(NfcAdapter.ACTION_NDEF_DISCOVERED);
        try {
            ndefFilter.addDataType("text/plain");
        } catch (IntentFilter.MalformedMimeTypeException e) {
            throw new RuntimeException("Failed to add MIME type.", e);
        }

        intentFiltersArray = new IntentFilter[]{ndefFilter};
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (nfcAdapter != null && nfcAdapter.isEnabled()) {
            nfcAdapter.enableForegroundDispatch(this, pendingIntent, intentFiltersArray, null);
        }
    }

    private void setupWebView() {
        eecs_oh = findViewById(R.id.eecs_oh_webpage);
        WebSettings webSettings = eecs_oh.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
            webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        String userAgent = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) AppleWebKit/537.36 "
                + "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36";
        webSettings.setUserAgentString(userAgent);

        eecs_oh.addJavascriptInterface(new WebAppInterface(this), "AndroidFunction");

        eecs_oh.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                String jsCode = ""
                        + "AndroidFunction.sendRoute(window.location.href);"
                        + "window.addEventListener('popstate', function() {"
                        + "  AndroidFunction.sendRoute(window.location.href);"
                        + "});"
                        + "(function(history){"
                        + "  var pushState = history.pushState;"
                        + "  history.pushState = function(state) {"
                        + "      pushState.apply(history, arguments);"
                        + "      AndroidFunction.sendRoute(window.location.href);"
                        + "  };"
                        + "})(window.history);";
                view.evaluateJavascript(jsCode, null);
            }
        });

        eecs_oh.setWebChromeClient(new WebChromeClient());
        eecs_oh.loadUrl("https://eecsoh.eecs.umich.edu/");
    }

    private void showNfcPrompt() {
        if (nfcDialog != null && nfcDialog.isShowing()) return;
        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setTitle("Scan NFC Tag")
                .setMessage("Please hold your device near an NFC tag to continue.")
                .setCancelable(true);
        nfcDialog = builder.create();
        nfcDialog.show();
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (nfcAdapter != null) {
            nfcAdapter.disableForegroundDispatch(this);
        }
        if (nfcDialog != null && nfcDialog.isShowing()) {
            nfcDialog.dismiss();
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (NfcAdapter.ACTION_NDEF_DISCOVERED.equals(intent.getAction())) {
            Parcelable[] rawMessages = intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES);
            if (rawMessages != null && rawMessages.length > 0) {
                NdefMessage message = (NdefMessage) rawMessages[0];
                NdefRecord record = message.getRecords()[0];
                byte[] payload = record.getPayload();

                String text = new String(payload, 3, payload.length - 3, StandardCharsets.UTF_8);
                TextView textView = findViewById(R.id.nfc_tag_message);
                textView.setText(text);
                textView.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));

                readNFC = true;

                if (nfcDialog != null && nfcDialog.isShowing()) {
                    nfcDialog.dismiss();
                }

                if (eecs_oh != null) {
                    String nfcText = text.replace("'", "\\'");
                    String fillJsCode =
                            "var fillValue = '" + nfcText + "';" +
                                    "var input = document.getElementsByClassName('input')[1];" +
                                    "if(input) {" +
                                    "  input.value = fillValue;" +
                                    "  input.dispatchEvent(new Event('input', { bubbles: true }));" +
                                    "  input.dispatchEvent(new Event('change', { bubbles: true }));" +
                                    "}";
                    eecs_oh.postDelayed(() -> {
                        eecs_oh.evaluateJavascript(fillJsCode, null);
                    }, 500);
                    Toast.makeText(MainActivity.this, "Location field updated", Toast.LENGTH_SHORT).show();
                }
            }
        }
    }

    @Override
    public void onBackPressed() {
        if (eecs_oh.canGoBack()) {
            eecs_oh.goBack();
        } else {
            super.onBackPressed();
        }
    }

    public class WebAppInterface {
        Context mContext;

        WebAppInterface(Context context) {
            mContext = context;
        }

        @JavascriptInterface
        public void sendRoute(String route) {
            Log.d("EECS_WEBVIEW", "Route changed: " + route);
            if (route != null && route.toLowerCase().contains("queues")) {
                runOnUiThread(() -> showNfcPrompt());
            }
        }
    }
}