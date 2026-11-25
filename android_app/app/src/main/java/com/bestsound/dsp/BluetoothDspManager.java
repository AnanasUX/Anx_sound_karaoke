package com.bestsound.dsp;

import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import java.io.IOException;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.UUID;

public class BluetoothDspManager {
    private static final String TAG = "BluetoothDspManager";

    // Standard Bluetooth Serial Port Profile (SPP) UUID
    private static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");

    public interface BluetoothCallback {
        void onBtConnected(String deviceName);
        void onBtDisconnected();
        void onBtTransmissionProgress(int currentPacket, int totalPackets);
        void onBtTransmissionComplete(String message);
        void onBtError(String error);
    }

    private final Context context;
    private final BluetoothAdapter bluetoothAdapter;
    private final Handler mainHandler;
    private BluetoothCallback callback;

    private BluetoothSocket socket;
    private OutputStream outputStream;
    private BluetoothDevice connectedDevice;
    private volatile boolean isConnecting = false;

    public BluetoothDspManager(Context context) {
        this.context = context;
        this.bluetoothAdapter = BluetoothAdapter.getDefaultAdapter();
        this.mainHandler = new Handler(Looper.getMainLooper());
    }

    public void setCallback(BluetoothCallback callback) {
        this.callback = callback;
    }

    public boolean isBluetoothSupported() {
        return bluetoothAdapter != null;
    }

    public boolean isBluetoothEnabled() {
        return bluetoothAdapter != null && bluetoothAdapter.isEnabled();
    }

    @SuppressLint("MissingPermission")
    public Set<BluetoothDevice> getPairedDevices() {
        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled()) {
            return Collections.emptySet();
        }
        try {
            return bluetoothAdapter.getBondedDevices();
        } catch (Exception e) {
            Log.e(TAG, "Error getting bonded devices: " + e.getMessage());
            return Collections.emptySet();
        }
    }

    public boolean isConnected() {
        return socket != null && socket.isConnected() && outputStream != null;
    }

    public String getConnectedDeviceName() {
        if (connectedDevice != null) {
            try {
                return connectedDevice.getName() != null ? connectedDevice.getName() : connectedDevice.getAddress();
            } catch (SecurityException ignored) {
                return connectedDevice.getAddress();
            }
        }
        return null;
    }

    @SuppressLint("MissingPermission")
    public void connect(BluetoothDevice device) {
        if (isConnecting) return;
        if (device == null) {
            if (callback != null) callback.onBtError("Chưa chọn thiết bị Bluetooth!");
            return;
        }

        disconnect();
        isConnecting = true;

        new Thread(() -> {
            try {
                // Cancel discovery because it slows down the connection
                if (bluetoothAdapter != null && bluetoothAdapter.isDiscovering()) {
                    bluetoothAdapter.cancelDiscovery();
                }
            } catch (Exception ignored) {}

            BluetoothSocket tmpSocket = null;
            String devName = device.getAddress();
            try {
                if (device.getName() != null) devName = device.getName();
            } catch (SecurityException ignored) {}

            final String finalDevName = devName;

            // Strategy 1: Standard SPP RFCOMM Socket
            try {
                tmpSocket = device.createRfcommSocketToServiceRecord(SPP_UUID);
                tmpSocket.connect();
            } catch (Exception e1) {
                Log.w(TAG, "Standard SPP failed, trying Insecure RFCOMM: " + e1.getMessage());
                try {
                    if (tmpSocket != null) tmpSocket.close();
                } catch (Exception ignored) {}

                // Strategy 2: Insecure RFCOMM Socket
                try {
                    tmpSocket = device.createInsecureRfcommSocketToServiceRecord(SPP_UUID);
                    tmpSocket.connect();
                } catch (Exception e2) {
                    Log.w(TAG, "Insecure SPP failed, trying reflection channel 1: " + e2.getMessage());
                    try {
                        if (tmpSocket != null) tmpSocket.close();
                    } catch (Exception ignored) {}

                    // Strategy 3: Hidden createRfcommSocket(int channel) via reflection (channel 1)
                    try {
                        Method m = device.getClass().getMethod("createRfcommSocket", int.class);
                        tmpSocket = (BluetoothSocket) m.invoke(device, 1);
                        if (tmpSocket != null) {
                            tmpSocket.connect();
                        }
                    } catch (Exception e3) {
                        Log.e(TAG, "All Bluetooth connection strategies failed: " + e3.getMessage());
                        try {
                            if (tmpSocket != null) tmpSocket.close();
                        } catch (Exception ignored) {}
                        isConnecting = false;
                        mainHandler.post(() -> {
                            if (callback != null) {
                                callback.onBtError("Không thể kết nối Bluetooth tới " + finalDevName + 
                                                   " (Vui lòng đảm bảo loa đang bật và đã ghép đôi Bluetooth)");
                            }
                        });
                        return;
                    }
                }
            }

            if (tmpSocket != null && tmpSocket.isConnected()) {
                try {
                    socket = tmpSocket;
                    outputStream = tmpSocket.getOutputStream();
                    connectedDevice = device;
                    isConnecting = false;

                    mainHandler.post(() -> {
                        if (callback != null) callback.onBtConnected(finalDevName);
                    });
                } catch (IOException e) {
                    isConnecting = false;
                    disconnect();
                    mainHandler.post(() -> {
                        if (callback != null) callback.onBtError("Không thể mở luồng truyền Bluetooth: " + e.getMessage());
                    });
                }
            } else {
                isConnecting = false;
                mainHandler.post(() -> {
                    if (callback != null) callback.onBtError("Kết nối thất bại tới " + finalDevName);
                });
            }
        }).start();
    }

    public void sendPacket(byte[] packet) {
        if (!isConnected()) {
            if (callback != null) callback.onBtError("Chưa kết nối Bluetooth tới loa!");
            return;
        }

        new Thread(() -> {
            boolean ok = writeRaw(packet);
            mainHandler.post(() -> {
                if (ok) {
                    if (callback != null) callback.onBtTransmissionComplete("Gửi lệnh Bluetooth thành công!");
                } else {
                    if (callback != null) callback.onBtError("Lỗi khi gửi lệnh qua Bluetooth!");
                }
            });
        }).start();
    }

    public void sendFullProfile(byte[] fullProfileBytes, String profileName) {
        if (!isConnected()) {
            if (callback != null) callback.onBtError("Chưa kết nối Bluetooth tới loa!");
            return;
        }

        new Thread(() -> {
            List<byte[]> frames = splitFrames(fullProfileBytes);
            int total = frames.size();

            for (int i = 0; i < total; i++) {
                byte[] frame = frames.get(i);
                boolean ok = writeRaw(frame);
                if (!ok) {
                    final int idx = i + 1;
                    mainHandler.post(() -> {
                        if (callback != null) callback.onBtError("Lỗi Bluetooth gói số " + idx + "/" + total);
                    });
                    return;
                }

                final int current = i + 1;
                mainHandler.post(() -> {
                    if (callback != null) callback.onBtTransmissionProgress(current, total);
                });

                try {
                    // Pacing delay between Bluetooth frames
                    Thread.sleep(15);
                } catch (InterruptedException ignored) {}
            }

            mainHandler.post(() -> {
                if (callback != null) callback.onBtTransmissionComplete("Đã truyền Profile qua Bluetooth: " + profileName);
            });
        }).start();
    }

    private synchronized boolean writeRaw(byte[] data) {
        if (outputStream == null) return false;
        try {
            outputStream.write(data);
            outputStream.flush();
            return true;
        } catch (IOException e) {
            Log.e(TAG, "Write error: " + e.getMessage());
            disconnect();
            mainHandler.post(() -> {
                if (callback != null) callback.onBtDisconnected();
            });
            return false;
        }
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

    public synchronized void disconnect() {
        if (outputStream != null) {
            try { outputStream.close(); } catch (Exception ignored) {}
            outputStream = null;
        }
        if (socket != null) {
            try { socket.close(); } catch (Exception ignored) {}
            socket = null;
        }
        connectedDevice = null;
        isConnecting = false;
    }

    public void destroy() {
        disconnect();
    }
}
