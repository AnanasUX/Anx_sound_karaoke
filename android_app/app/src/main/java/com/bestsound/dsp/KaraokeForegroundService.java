package com.bestsound.dsp;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Binder;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

/**
 * Foreground Service keeping the Low-Latency Karaoke Engine alive when the user
 * switches to another app (e.g. YouTube for lyrics) or turns off the screen.
 */
public class KaraokeForegroundService extends Service {
    public static final String CHANNEL_ID = "bestsound_karaoke_live_channel";
    public static final int NOTIFICATION_ID = 2026;
    public static final String ACTION_START = "com.bestsound.karaoke.ACTION_START";
    public static final String ACTION_STOP = "com.bestsound.karaoke.ACTION_STOP";

    private static volatile NativeKaraokeEngine sharedEngine;
    private static volatile boolean isServiceRunning = false;
    private PowerManager.WakeLock wakeLock;

    public interface ServiceStateListener {
        void onServiceStopped();
    }

    private static ServiceStateListener stateListener;

    public static void setStateListener(ServiceStateListener listener) {
        stateListener = listener;
    }

    public static NativeKaraokeEngine getEngine(Context context) {
        if (sharedEngine == null) {
            synchronized (KaraokeForegroundService.class) {
                if (sharedEngine == null) {
                    sharedEngine = new NativeKaraokeEngine(context.getApplicationContext());
                }
            }
        }
        return sharedEngine;
    }

    public static boolean isRunning() {
        return isServiceRunning && sharedEngine != null && sharedEngine.isRunning();
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : ACTION_START;

        if (ACTION_STOP.equals(action)) {
            stopKaraokeAndService();
            return START_NOT_STICKY;
        }

        Notification notification = buildNotification();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE | ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            );
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }

        acquireWakeLock();

        NativeKaraokeEngine engine = getEngine(this);
        if (!engine.isRunning()) {
            engine.start();
        }
        isServiceRunning = true;

        return START_STICKY;
    }

    private void stopKaraokeAndService() {
        isServiceRunning = false;
        if (sharedEngine != null) {
            sharedEngine.stop();
        }
        releaseWakeLock();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } else {
            stopForeground(true);
        }
        stopSelf();
        if (stateListener != null) {
            stateListener.onServiceStopped();
        }
    }

    private void acquireWakeLock() {
        if (wakeLock == null) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BestSound::KaraokeWakeLock");
                wakeLock.setReferenceCounted(false);
            }
        }
        if (wakeLock != null && !wakeLock.isHeld()) {
            wakeLock.acquire(4 * 60 * 60 * 1000L); // Up to 4 hours max safety timeout
        }
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {}
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Ansound Karaoke Live",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Giữ Micro & Vang số chạy nền khi tắt màn hình hoặc mở ứng dụng khác");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildNotification() {
        Intent openIntent = new Intent(this, MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPending = PendingIntent.getActivity(
                this, 0, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Intent stopIntent = new Intent(this, KaraokeForegroundService.class);
        stopIntent.setAction(ACTION_STOP);
        PendingIntent stopPending = PendingIntent.getService(
                this, 1, stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }

        return builder
                .setContentTitle("🎤 Ansound Vang Số Karaoke đang chạy nền")
                .setContentText("Mic điện thoại đang hoạt động · Chạm để mở lại")
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentIntent(openPending)
                .addAction(new Notification.Action.Builder(
                        android.R.drawable.ic_media_pause,
                        "TẮT MICRO",
                        stopPending
                ).build())
                .setOngoing(true)
                .build();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        isServiceRunning = false;
        if (sharedEngine != null) {
            sharedEngine.stop();
        }
        releaseWakeLock();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return new Binder();
    }
}
