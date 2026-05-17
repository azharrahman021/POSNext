# POS Next Android Bluetooth Printing

This folder contains the native Android Capacitor plugin used by POS Next to
print directly to paired classic Bluetooth ESC/POS receipt printers.

## How it works

- The Vue app checks for `window.Capacitor.Plugins.PosBluetoothPrinter`.
- When present, `Silent Print` sends ESC/POS bytes directly to the selected
  paired Bluetooth printer.
- When absent, POS Next keeps the existing QZ Tray/browser print behavior.

## Install into a Capacitor Android app

1. Add Capacitor to `apps/pos_next/POS`:

   ```bash
   yarn add @capacitor/core @capacitor/android
   yarn add -D @capacitor/cli
   ```

2. Create `capacitor.config.json` in `apps/pos_next/POS`. For a packaged app
   that loads the built POS assets, use:

   ```json
   {
     "appId": "com.posnext.app",
     "appName": "POS Next",
     "webDir": "../pos_next/public/pos"
   }
   ```

   For a wrapper that loads your ERPNext site directly, add:

   ```json
   {
     "server": {
       "url": "https://your-erpnext-site.example.com/pos",
       "cleartext": false
     }
   }
   ```

3. Build and add Android:

   ```bash
   yarn build
   npx cap add android
   npx cap sync android
   ```

4. Copy `com/posnext/printer/PosBluetoothPrinterPlugin.java` into:

   ```text
   android/app/src/main/java/com/posnext/printer/PosBluetoothPrinterPlugin.java
   ```

5. Register the plugin in `android/app/src/main/java/<your app package>/MainActivity.java`:

   ```java
   package com.posnext.app;

   import android.os.Bundle;
   import com.getcapacitor.BridgeActivity;
   import com.posnext.printer.PosBluetoothPrinterPlugin;

   public class MainActivity extends BridgeActivity {
     @Override
     public void onCreate(Bundle savedInstanceState) {
       registerPlugin(PosBluetoothPrinterPlugin.class);
       super.onCreate(savedInstanceState);
     }
   }
   ```

6. Add these permissions to `android/app/src/main/AndroidManifest.xml`:

   ```xml
   <uses-permission android:name="android.permission.BLUETOOTH" />
   <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
   <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
   <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
   <uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
   ```

7. Pair the receipt printer in Android Settings, open POS Next, enable
   `Silent Print`, refresh the printer list, and select the Bluetooth printer.

## Notes

- This targets classic Bluetooth SPP printers using the standard ESC/POS serial
  UUID. BLE-only printers usually need a vendor SDK and will not work with this
  plugin as-is.
- The current receipt output is text ESC/POS. It is reliable for common thermal
  printers, but complex HTML print formats, logos, and non-Latin code pages may
  need printer-specific ESC/POS work.
