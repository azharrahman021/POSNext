package com.posnext.printer;

import android.Manifest;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import android.os.Build;
import android.util.Base64;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import org.json.JSONObject;

import java.io.OutputStream;
import java.util.Set;
import java.util.UUID;

@CapacitorPlugin(
	name = "PosBluetoothPrinter",
	permissions = {
		@Permission(
			alias = "bluetooth",
			strings = {
				Manifest.permission.BLUETOOTH,
				Manifest.permission.BLUETOOTH_ADMIN,
				Manifest.permission.ACCESS_FINE_LOCATION,
				Manifest.permission.BLUETOOTH_CONNECT,
				Manifest.permission.BLUETOOTH_SCAN
			}
		)
	}
)
public class PosBluetoothPrinterPlugin extends Plugin {
	private static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");

	@PluginMethod
	public void isAvailable(PluginCall call) {
		JSObject result = new JSObject();
		result.put("available", BluetoothAdapter.getDefaultAdapter() != null);
		call.resolve(result);
	}

	@PluginMethod
	public void listPairedPrinters(PluginCall call) {
		if (!hasBluetoothPermission()) {
			requestPermissionForAlias("bluetooth", call, "bluetoothPermissionsCallback");
			return;
		}

		BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
		if (adapter == null) {
			call.reject("Bluetooth is not available on this device");
			return;
		}

		try {
			JSArray printers = new JSArray();
			Set<BluetoothDevice> devices = adapter.getBondedDevices();
			for (BluetoothDevice device : devices) {
				JSONObject printer = new JSONObject();
				printer.put("name", device.getName());
				printer.put("address", device.getAddress());
				printers.put(printer);
			}

			JSObject result = new JSObject();
			result.put("printers", printers);
			call.resolve(result);
		} catch (Exception error) {
			call.reject("Failed to list paired Bluetooth devices", error);
		}
	}

	@PluginMethod
	public void printRawBase64(PluginCall call) {
		if (!hasBluetoothPermission()) {
			requestPermissionForAlias("bluetooth", call, "bluetoothPermissionsCallback");
			return;
		}

		String address = call.getString("address");
		String data = call.getString("data");
		if (address == null || address.isEmpty()) {
			call.reject("Bluetooth printer address is required");
			return;
		}
		if (data == null || data.isEmpty()) {
			call.reject("Print data is required");
			return;
		}

		new Thread(() -> {
			BluetoothSocket socket = null;
			try {
				BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
				if (adapter == null) {
					call.reject("Bluetooth is not available on this device");
					return;
				}

				BluetoothDevice device = adapter.getRemoteDevice(address);
				socket = device.createRfcommSocketToServiceRecord(SPP_UUID);
				adapter.cancelDiscovery();
				socket.connect();

				byte[] payload = Base64.decode(data, Base64.DEFAULT);
				OutputStream outputStream = socket.getOutputStream();
				outputStream.write(payload);
				outputStream.flush();

				JSObject result = new JSObject();
				result.put("printed", true);
				call.resolve(result);
			} catch (Exception error) {
				call.reject("Bluetooth print failed: " + error.getMessage(), error);
			} finally {
				if (socket != null) {
					try {
						socket.close();
					} catch (Exception ignored) {
						// Ignore close failures after the print attempt is complete.
					}
				}
			}
		}).start();
	}

	private boolean hasBluetoothPermission() {
		if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
			return true;
		}
		return getPermissionState("bluetooth") == PermissionState.GRANTED;
	}

	@PermissionCallback
	private void bluetoothPermissionsCallback(PluginCall call) {
		if (!hasBluetoothPermission()) {
			call.reject("Bluetooth permission was not granted");
			return;
		}

		if (call.getString("data") != null) {
			printRawBase64(call);
			return;
		}

		listPairedPrinters(call);
	}
}
