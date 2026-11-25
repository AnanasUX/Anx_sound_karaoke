package com.bestsound.dsp;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbConstants;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

public class UsbDspManager {
    private static final String TAG = "UsbDspManager";
    public static final String ACTION_USB_PERMISSION = "com.bestsound.dsp.USB_PERMISSION";

    public interface DspCallback {
        void onDeviceConnected(String deviceName);
        void onDeviceDisconnected();
        void onTransmissionProgress(int currentPacket, int totalPackets);
        void onTransmissionComplete(String message);
        void onError(String error);
    }

    private final Context context;
    private final UsbManager usbManager;
    private final Handler mainHandler;
    private DspCallback callback;

    private UsbDevice connectedDevice;
    private UsbDeviceConnection connection;
    private UsbInterface activeInterface;
    private UsbEndpoint endpointOut;
    private UsbEndpoint endpointIn;

    private final BroadcastReceiver usbReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context ctx, Intent intent) {
            String action = intent.getAction();
            if (ACTION_USB_PERMISSION.equals(action)) {
                synchronized (this) {
                    UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                    if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) {
                        if (device != null) {
                            openDevice(device);
                        }
                    } else {
                        if (callback != null) callback.onError("Người dùng từ chối cấp quyền USB!");
                    }
                }
            } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(action)) {
                UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                if (device != null && device.equals(connectedDevice)) {
                    closeConnection();
                    if (callback != null) callback.onDeviceDisconnected();
                }
            }
        }
    };

    public UsbDspManager(Context context) {
        this.context = context;
        this.usbManager = (UsbManager) context.getSystemService(Context.USB_SERVICE);
        this.mainHandler = new Handler(Looper.getMainLooper());

        IntentFilter filter = new IntentFilter();
        filter.addAction(ACTION_USB_PERMISSION);
        filter.addAction(UsbManager.ACTION_USB_DEVICE_DETACHED);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.registerReceiver(usbReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            context.registerReceiver(usbReceiver, filter);
        }
    }

    public void setCallback(DspCallback callback) {
        this.callback = callback;
    }

    public boolean isConnected() {
        return connection != null && activeInterface != null;
    }

    public void connect() {
        if (usbManager == null) {
            if (callback != null) callback.onError("Điện thoại không hỗ trợ USB Host (OTG)!");
            return;
        }

        HashMap<String, UsbDevice> deviceList = usbManager.getDeviceList();
        if (deviceList.isEmpty()) {
            if (callback != null) callback.onError("Chưa tìm thấy thiết bị USB! Hãy cắm cáp Type-C vào mạch loa và bật nguồn loa.");
            return;
        }

        // Search for Best Sound / MVSilicon or take the first connected device
        UsbDevice targetDevice = null;
        for (UsbDevice dev : deviceList.values()) {
            String name = (dev.getProductName() != null ? dev.getProductName() : "") + " " +
                          (dev.getManufacturerName() != null ? dev.getManufacturerName() : "");
            if (name.toLowerCase().contains("best") || 
                name.toLowerCase().contains("sound") || 
                name.toLowerCase().contains("mvsilicon") ||
                name.toLowerCase().contains("audio") ||
                dev.getVendorId() == 0x4C4A || dev.getVendorId() == 0x8888) {
                targetDevice = dev;
                break;
            }
        }

        if (targetDevice == null) {
            // Take the first available non-host device
            targetDevice = deviceList.values().iterator().next();
        }

        if (usbManager.hasPermission(targetDevice)) {
            openDevice(targetDevice);
        } else {
            int flags = 0;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                flags = PendingIntent.FLAG_MUTABLE;
            }
            PendingIntent permissionIntent = PendingIntent.getBroadcast(
                    context, 0, new Intent(ACTION_USB_PERMISSION), flags);
            usbManager.requestPermission(targetDevice, permissionIntent);
        }
    }

    private void openDevice(UsbDevice device) {
        closeConnection();
        connectedDevice = device;

        UsbDeviceConnection conn = usbManager.openDevice(device);
        if (conn == null) {
            if (callback != null) callback.onError("Không thể mở kết nối USB tới loa (Lỗi openDevice)!");
            return;
        }

        this.connection = conn;
        UsbInterface selectedIntf = null;
        UsbEndpoint outEp = null;
        UsbEndpoint inEp = null;

        // Find HID interface (0x03) or vendor specific (0xFF) or interface with OUT endpoint
        for (int i = 0; i < device.getInterfaceCount(); i++) {
            UsbInterface intf = device.getInterface(i);
            UsbEndpoint candidateOut = null;
            UsbEndpoint candidateIn = null;

            for (int e = 0; e < intf.getEndpointCount(); e++) {
                UsbEndpoint ep = intf.getEndpoint(e);
                if (ep.getDirection() == UsbConstants.USB_DIR_OUT) {
                    candidateOut = ep;
                } else if (ep.getDirection() == UsbConstants.USB_DIR_IN) {
                    candidateIn = ep;
                }
            }

            if (intf.getInterfaceClass() == UsbConstants.USB_CLASS_HID || candidateOut != null) {
                selectedIntf = intf;
                outEp = candidateOut;
                inEp = candidateIn;
                break;
            }
        }

        if (selectedIntf == null && device.getInterfaceCount() > 0) {
            selectedIntf = device.getInterface(0);
        }

        if (selectedIntf != null) {
            conn.claimInterface(selectedIntf, true);
            this.activeInterface = selectedIntf;
            this.endpointOut = outEp;
            this.endpointIn = inEp;

            String devName = device.getProductName() != null ? device.getProductName() : "Best Sound T1V2 (DSP)";
            if (callback != null) callback.onDeviceConnected(devName);
        } else {
            if (callback != null) callback.onError("Không tìm thấy interface giao tiếp USB phù hợp!");
        }
    }

    public void sendPacket(byte[] packet) {
        if (!isConnected()) {
            if (callback != null) callback.onError("Chưa kết nối USB tới loa!");
            return;
        }

        new Thread(() -> {
            boolean success = transferRaw(packet);
            mainHandler.post(() -> {
                if (success) {
                    if (callback != null) callback.onTransmissionComplete("Gửi lệnh thành công!");
                } else {
                    if (callback != null) callback.onError("Lỗi khi gửi gói dữ liệu USB!");
                }
            });
        }).start();
    }

    public void sendFullProfile(byte[] fullProfileBytes, String profileName) {
        if (!isConnected()) {
            if (callback != null) callback.onError("Chưa kết nối USB tới loa!");
            return;
        }

        new Thread(() -> {
            // Split full stream into individual frames (starts with 0xA5 0x5A)
            List<byte[]> frames = splitFrames(fullProfileBytes);
            int total = frames.size();

            for (int i = 0; i < total; i++) {
                byte[] frame = frames.get(i);
                boolean ok = transferRaw(frame);
                if (!ok) {
                    final int idx = i + 1;
                    mainHandler.post(() -> {
                        if (callback != null) callback.onError("Lỗi truyền gói số " + idx + "/" + total);
                    });
                    return;
                }

                final int current = i + 1;
                mainHandler.post(() -> {
                    if (callback != null) callback.onTransmissionProgress(current, total);
                });

                try {
                    Thread.sleep(12); // Short pacing delay between DSP frames
                } catch (InterruptedException ignored) {}
            }

            mainHandler.post(() -> {
                if (callback != null) callback.onTransmissionComplete("Đã nạp thành công Profile: " + profileName);
            });
        }).start();
    }

    private boolean transferRaw(byte[] data) {
        if (connection == null) return false;

        // Try Bulk/Interrupt OUT endpoint first
        if (endpointOut != null) {
            int sent = connection.bulkTransfer(endpointOut, data, data.length, 1000);
            if (sent >= 0) return true;
        }

        // Fallback to HID Set_Report control transfer (0x21, 0x09)
        int intfId = activeInterface != null ? activeInterface.getId() : 0;
        int sentCtrl = connection.controlTransfer(0x21, 0x09, 0x0200, intfId, data, data.length, 1000);
        return sentCtrl >= 0;
    }

    private List<byte[]> splitFrames(byte[] stream) {
        List<byte[]> frames = new ArrayList<>();
        int i = 0;
        while (i < stream.length) {
            if (i + 1 < stream.length && (stream[i] & 0xFF) == 0xA5 && (stream[i+1] & 0xFF) == 0x5A) {
                int j = i + 2;
                while (j < stream.length) {
                    if ((stream[j] & 0xFF) == 0x16) {
                        j++;
                        break;
                    }
                    if (j + 1 < stream.length && (stream[j] & 0xFF) == 0xA5 && (stream[j+1] & 0xFF) == 0x5A) {
                        break;
                    }
                    j++;
                }
                byte[] frame = new byte[j - i];
                System.arraycopy(stream, i, frame, 0, frame.length);
                frames.add(frame);
                i = j;
            } else {
                i++;
            }
        }
        return frames;
    }

    public void closeConnection() {
        if (connection != null) {
            if (activeInterface != null) {
                try {
                    connection.releaseInterface(activeInterface);
                } catch (Exception ignored) {}
            }
            try {
                connection.close();
            } catch (Exception ignored) {}
        }
        connection = null;
        activeInterface = null;
        endpointOut = null;
        endpointIn = null;
        connectedDevice = null;
    }

    public void destroy() {
        closeConnection();
        try {
            context.unregisterReceiver(usbReceiver);
        } catch (Exception ignored) {}
    }
}
