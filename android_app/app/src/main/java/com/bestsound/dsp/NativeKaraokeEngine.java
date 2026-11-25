package com.bestsound.dsp;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioDeviceInfo;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.AudioTrack;
import android.media.MediaRecorder;
import android.media.audiofx.AcousticEchoCanceler;
import android.media.audiofx.AutomaticGainControl;
import android.media.audiofx.NoiseSuppressor;
import android.os.Build;
import android.os.Process;
import android.util.Log;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.RandomAccessFile;

/**
 * Full-Duplex Low-Latency Audio DSP Engine for An Sound.
 *
 * Implements 4-layer architecture:
 * 1. Explicit Input/Output Routing: Forces BUILTIN_MIC (fixes TRS/TRRS AUX mic-drop bug)
 *    and routes output to A2DP / WIRED_AUX / SPEAKER in MODE_NORMAL (prevents HFP/SCO 8kHz drop).
 * 2. Low-Latency Zero-Allocation Pipeline: Uses VOICE_PERFORMANCE / UNPROCESSED raw capture
 *    and PERFORMANCE_MODE_LOW_LATENCY AudioTrack without OS AEC/NS/AGC voice-chopping.
 * 3. Real-time DSP Chain:
 *    [1] LR24 HPF (80-100Hz) -> [2] dBFS Noise Gate (-55 to -20dBFS) ->
 *    [3] SSB Frequency Shifter (+4Hz anti-howling) + Notch -> [4] 3:1 Compressor & -2.0dBFS Limiter ->
 *    [5] 3-Band Vocal EQ + Echo + Schroeder Reverb.
 */
public class NativeKaraokeEngine {
    private static final String TAG = "NativeKaraokeEngine";

    public static final String ROUTE_AUTO = "AUTO";
    public static final String ROUTE_BLUETOOTH = "BLUETOOTH";
    public static final String ROUTE_AUX = "AUX";
    public static final String ROUTE_SPEAKER = "SPEAKER";

    private final Context context;
    private volatile boolean isRunning = false;
    private Thread audioThread;

    private AudioRecord audioRecord;
    private AudioTrack audioTrack;
    private AutomaticGainControl agc;

    // Routing state
    private volatile String preferredOutputRoute = ROUTE_AUTO;
    private volatile boolean forceBuiltInMic = true;

    // Live DSP parameters (thread-safe volatile)
    private volatile float micGain = 1.25f;          // 0.0 - 3.5
    private volatile float dryLevel = 1.00f;         // 0.0 - 1.0
    private volatile float gateThresholdDb = -40.0f; // -55.0 to -20.0 dBFS
    private volatile float hpfCutoffHz = 90.0f;      // 80.0 - 120.0 Hz (LR24)
    private volatile boolean lowCutEnabled = true;
    private volatile boolean freqShiftEnabled = true; // +4Hz SSB Frequency Shifter anti-howling
    private volatile float freqShiftHz = 4.0f;        // +3Hz to +5Hz
    private volatile boolean antiHowlNotch = true;

    // Vocal EQ & FX
    private volatile float echoMix = 0.15f;
    private volatile int echoDelayMs = 180;
    private volatile float echoFeedback = 0.25f;
    private volatile float reverbMix = 0.15f;
    private volatile float reverbDecay = 0.68f;
    private volatile float bassDb = 1.0f;
    private volatile float midDb = 1.0f;
    private volatile float trebleDb = 1.5f;
    private volatile float stereoChorus = 0.0f;

    // Telemetry
    private volatile float currentDb = -80.0f;
    private volatile float estimatedLatencyMs = 0.0f;
    private volatile int activeSampleRate = 48000;

    // Live WAV Recording
    private volatile boolean isRecordingWav = false;
    private BufferedOutputStream wavOutStream;
    private File wavFile;
    private long wavDataBytes = 0;
    private final Object recLock = new Object();

    public interface MeterCallback {
        void onMeterUpdate(float db, float latencyMs);
    }

    private MeterCallback meterCallback;

    public NativeKaraokeEngine(Context context) {
        this.context = context.getApplicationContext();
    }

    public void setMeterCallback(MeterCallback callback) {
        this.meterCallback = callback;
    }

    public boolean isRunning() { return isRunning; }
    public float getCurrentDb() { return currentDb; }
    public float getEstimatedLatencyMs() { return estimatedLatencyMs; }

    // Routing controls
    public void setPreferredOutputRoute(String route) {
        this.preferredOutputRoute = route != null ? route : ROUTE_AUTO;
        applyOutputRouting();
    }

    public void setForceBuiltInMic(boolean force) {
        this.forceBuiltInMic = force;
        if (audioRecord != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            audioRecord.setPreferredDevice(force ? findBuiltInMic() : null);
        }
    }

    // DSP setters
    public void setMicGain(float gain) { this.micGain = Math.max(0f, Math.min(3.5f, gain)); }
    public void setDryLevel(float level) { this.dryLevel = Math.max(0f, Math.min(1.0f, level)); }
    public void setGateThresholdDb(float db) { this.gateThresholdDb = Math.max(-55.0f, Math.min(-20.0f, db)); }
    public void setNearFieldLevel(float level) {
        // Maps 0.0..1.0 slider to -55dBFS..-25dBFS
        this.gateThresholdDb = -55.0f + Math.max(0f, Math.min(1f, level)) * 30.0f;
    }
    public void setHpfCutoffHz(float hz) { this.hpfCutoffHz = Math.max(60f, Math.min(140f, hz)); }
    public void setLowCutEnabled(boolean enabled) { this.lowCutEnabled = enabled; }
    public void setFreqShiftEnabled(boolean enabled) { this.freqShiftEnabled = enabled; }
    public void setAntiHowlEnabled(boolean enabled) {
        this.antiHowlNotch = enabled;
        this.freqShiftEnabled = enabled;
    }
    public void setEchoMix(float mix) { this.echoMix = Math.max(0f, Math.min(1.0f, mix)); }
    public void setEchoDelayMs(int ms) { this.echoDelayMs = Math.max(50, Math.min(450, ms)); }
    public void setEchoFeedback(float fb) { this.echoFeedback = Math.max(0f, Math.min(0.75f, fb)); }
    public void setReverbMix(float mix) { this.reverbMix = Math.max(0f, Math.min(1.0f, mix)); }
    public void setReverbSize(float seconds) {
        float norm = (seconds - 0.5f) / 3.5f;
        this.reverbDecay = 0.55f + Math.max(0f, Math.min(1f, norm)) * 0.32f;
    }
    public void setBassDb(float db) { this.bassDb = Math.max(-9f, Math.min(9f, db)); }
    public void setMidDb(float db) { this.midDb = Math.max(-9f, Math.min(9f, db)); }
    public void setTrebleDb(float db) { this.trebleDb = Math.max(-9f, Math.min(9f, db)); }
    public void setToneDb(float db) { this.trebleDb = Math.max(-9f, Math.min(9f, db)); }
    public void setStereoChorus(float mix) { this.stereoChorus = Math.max(0f, Math.min(1f, mix)); }
    public void setHwAecEnabled(boolean ignored) {
        // OS voice AEC/NS intentionally bypassed to keep singing fidelity intact
    }

    public boolean startWavRecording(File outputFile) {
        if (!isRunning) return false;
        synchronized (recLock) {
            if (isRecordingWav) return true;
            try {
                File parent = outputFile.getParentFile();
                if (parent != null && !parent.exists()) parent.mkdirs();
                wavFile = outputFile;
                wavOutStream = new BufferedOutputStream(new FileOutputStream(outputFile), 16384);
                wavOutStream.write(new byte[44]);
                wavDataBytes = 0;
                isRecordingWav = true;
                return true;
            } catch (Exception e) {
                Log.e(TAG, "Failed to start WAV recording", e);
                return false;
            }
        }
    }

    public String stopWavRecording() {
        synchronized (recLock) {
            if (!isRecordingWav) return null;
            isRecordingWav = false;
            try {
                if (wavOutStream != null) {
                    wavOutStream.flush();
                    wavOutStream.close();
                    wavOutStream = null;
                }
                if (wavFile != null && wavFile.exists()) {
                    writeWavHeader(wavFile, activeSampleRate, 2, 16, wavDataBytes);
                    return wavFile.getAbsolutePath();
                }
            } catch (Exception e) {
                Log.e(TAG, "Failed to finalize WAV recording", e);
            }
            return null;
        }
    }

    private void writeWavHeader(File file, int sampleRate, int channels, int bitsPerSample, long dataLen) throws Exception {
        long byteRate = (long) sampleRate * channels * bitsPerSample / 8;
        int blockAlign = channels * bitsPerSample / 8;
        long chunkSize = 36 + dataLen;
        byte[] header = new byte[44];
        header[0] = 'R'; header[1] = 'I'; header[2] = 'F'; header[3] = 'F';
        header[4] = (byte) (chunkSize & 0xff);
        header[5] = (byte) ((chunkSize >> 8) & 0xff);
        header[6] = (byte) ((chunkSize >> 16) & 0xff);
        header[7] = (byte) ((chunkSize >> 24) & 0xff);
        header[8] = 'W'; header[9] = 'A'; header[10] = 'V'; header[11] = 'E';
        header[12] = 'f'; header[13] = 'm'; header[14] = 't'; header[15] = ' ';
        header[16] = 16; header[17] = 0; header[18] = 0; header[19] = 0;
        header[20] = 1; header[21] = 0;
        header[22] = (byte) channels; header[23] = 0;
        header[24] = (byte) (sampleRate & 0xff);
        header[25] = (byte) ((sampleRate >> 8) & 0xff);
        header[26] = (byte) ((sampleRate >> 16) & 0xff);
        header[27] = (byte) ((sampleRate >> 24) & 0xff);
        header[28] = (byte) (byteRate & 0xff);
        header[29] = (byte) ((byteRate >> 8) & 0xff);
        header[30] = (byte) ((byteRate >> 16) & 0xff);
        header[31] = (byte) ((byteRate >> 24) & 0xff);
        header[32] = (byte) blockAlign; header[33] = 0;
        header[34] = (byte) bitsPerSample; header[35] = 0;
        header[36] = 'd'; header[37] = 'a'; header[38] = 't'; header[39] = 'a';
        header[40] = (byte) (dataLen & 0xff);
        header[41] = (byte) ((dataLen >> 8) & 0xff);
        header[42] = (byte) ((dataLen >> 16) & 0xff);
        header[43] = (byte) ((dataLen >> 24) & 0xff);

        try (RandomAccessFile raf = new RandomAccessFile(file, "rw")) {
            raf.seek(0);
            raf.write(header);
        }
    }

    public synchronized boolean start() {
        if (isRunning) return true;

        // Layer 1: Ensure MODE_NORMAL & Bluetooth SCO OFF so A2DP Stereo 44.1/48kHz is preserved
        enforceCleanAudioMode();

        int sampleRate = getOptimalSampleRate();
        int channelIn = AudioFormat.CHANNEL_IN_MONO;
        int channelOut = AudioFormat.CHANNEL_OUT_STEREO;
        int encoding = AudioFormat.ENCODING_PCM_16BIT;

        int minInBuf = AudioRecord.getMinBufferSize(sampleRate, channelIn, encoding);
        int minOutBuf = AudioTrack.getMinBufferSize(sampleRate, channelOut, encoding);
        if (minInBuf <= 0 || minOutBuf <= 0) {
            sampleRate = 44100;
            minInBuf = AudioRecord.getMinBufferSize(sampleRate, channelIn, encoding);
            minOutBuf = AudioTrack.getMinBufferSize(sampleRate, channelOut, encoding);
        }
        activeSampleRate = sampleRate;

        // Layer 2: Hardware-aligned burst frame (128 or 256 samples)
        final int burstFrames = getOptimalFramesPerBuffer();
        final int frameSamples = Math.max(128, Math.min(256, burstFrames));
        final int recBufBytes = Math.max(minInBuf, frameSamples * 2 * 2);
        final int playBufBytes = Math.max(minOutBuf, frameSamples * 4 * 2);

        try {
            // Select raw singing source (VOICE_PERFORMANCE -> UNPROCESSED -> MIC)
            // Disables OS AEC/NS/AGC so singing timbre isn't chopped!
            int audioSource = selectSingingAudioSource();
            audioRecord = new AudioRecord(audioSource, sampleRate, channelIn, encoding, recBufBytes);

            if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
                audioRecord.release();
                audioRecord = new AudioRecord(MediaRecorder.AudioSource.MIC, sampleRate, channelIn, encoding, recBufBytes);
            }
            if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord failed to initialize");
                releaseResources();
                return false;
            }

            // Force BUILTIN_MIC so TRS/TRRS AUX cable never disconnects phone mic
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && forceBuiltInMic) {
                AudioDeviceInfo builtInMic = findBuiltInMic();
                if (builtInMic != null) {
                    audioRecord.setPreferredDevice(builtInMic);
                }
            }

            // Explicitly disable hardware AGC if present
            if (AutomaticGainControl.isAvailable()) {
                agc = AutomaticGainControl.create(audioRecord.getAudioSessionId());
                if (agc != null) agc.setEnabled(false);
            }

            AudioAttributes attrs = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build();

            AudioFormat outFormat = new AudioFormat.Builder()
                    .setSampleRate(sampleRate)
                    .setChannelMask(channelOut)
                    .setEncoding(encoding)
                    .build();

            AudioTrack.Builder trackBuilder = new AudioTrack.Builder()
                    .setAudioAttributes(attrs)
                    .setAudioFormat(outFormat)
                    .setBufferSizeInBytes(playBufBytes)
                    .setTransferMode(AudioTrack.MODE_STREAM);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                trackBuilder.setPerformanceMode(AudioTrack.PERFORMANCE_MODE_LOW_LATENCY);
            }

            audioTrack = trackBuilder.build();
            if (audioTrack.getState() != AudioTrack.STATE_INITIALIZED) {
                Log.e(TAG, "AudioTrack failed to initialize");
                releaseResources();
                return false;
            }
            audioTrack.setVolume(1.0f);

            // Apply explicit output device routing (A2DP / AUX / SPEAKER)
            applyOutputRouting();

            // Estimate pipeline latency in ms
            int inFrames = recBufBytes / 2;
            int outFrames = (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)
                    ? audioTrack.getBufferSizeInFrames()
                    : (playBufBytes / 4);
            estimatedLatencyMs = (inFrames + outFrames) * 1000.0f / sampleRate;

            isRunning = true;
            final int finalSampleRate = sampleRate;
            audioThread = new Thread(() -> processAudioLoop(finalSampleRate, frameSamples), "AnSoundDspThread");
            audioThread.start();
            return true;

        } catch (SecurityException se) {
            Log.e(TAG, "Missing RECORD_AUDIO permission", se);
            releaseResources();
            return false;
        } catch (Exception e) {
            Log.e(TAG, "Error starting NativeKaraokeEngine", e);
            releaseResources();
            return false;
        }
    }

    private void enforceCleanAudioMode() {
        try {
            AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            if (am != null) {
                am.setMode(AudioManager.MODE_NORMAL);
                am.stopBluetoothSco();
                am.setBluetoothScoOn(false);
            }
        } catch (Exception ignored) {}
    }

    public void applyOutputRouting() {
        if (audioTrack == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return;
        AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        if (am == null) return;

        AudioDeviceInfo target = null;
        AudioDeviceInfo[] outputs = am.getDevices(AudioManager.GET_DEVICES_OUTPUTS);

        if (ROUTE_BLUETOOTH.equals(preferredOutputRoute)) {
            for (AudioDeviceInfo dev : outputs) {
                int t = dev.getType();
                if (t == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP || t == AudioDeviceInfo.TYPE_BLE_SPEAKER || t == AudioDeviceInfo.TYPE_BLE_HEADSET) {
                    target = dev;
                    break;
                }
            }
        } else if (ROUTE_AUX.equals(preferredOutputRoute)) {
            for (AudioDeviceInfo dev : outputs) {
                int t = dev.getType();
                if (t == AudioDeviceInfo.TYPE_WIRED_HEADSET || t == AudioDeviceInfo.TYPE_WIRED_HEADPHONES || t == AudioDeviceInfo.TYPE_USB_HEADSET) {
                    target = dev;
                    break;
                }
            }
        } else if (ROUTE_SPEAKER.equals(preferredOutputRoute)) {
            for (AudioDeviceInfo dev : outputs) {
                if (dev.getType() == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
                    target = dev;
                    break;
                }
            }
        }
        // ROUTE_AUTO -> target stays null (OS picks active A2DP / AUX / Speaker)
        audioTrack.setPreferredDevice(target);
    }

    private int selectSingingAudioSource() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            return MediaRecorder.AudioSource.VOICE_PERFORMANCE;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            if (am != null && "true".equalsIgnoreCase(am.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED))) {
                return MediaRecorder.AudioSource.UNPROCESSED;
            }
        }
        return MediaRecorder.AudioSource.MIC;
    }

    public synchronized void stop() {
        stopWavRecording();
        isRunning = false;
        if (audioThread != null) {
            try { audioThread.join(400); } catch (InterruptedException ignored) {}
            audioThread = null;
        }
        releaseResources();
        currentDb = -80.0f;
    }

    private void releaseResources() {
        if (agc != null) { try { agc.release(); } catch (Exception ignored) {} agc = null; }
        if (audioRecord != null) {
            try {
                if (audioRecord.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) audioRecord.stop();
                audioRecord.release();
            } catch (Exception ignored) {}
            audioRecord = null;
        }
        if (audioTrack != null) {
            try {
                if (audioTrack.getPlayState() == AudioTrack.PLAYSTATE_PLAYING) audioTrack.stop();
                audioTrack.release();
            } catch (Exception ignored) {}
            audioTrack = null;
        }
    }

    private int getOptimalSampleRate() {
        AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        if (am != null) {
            String rateStr = am.getProperty(AudioManager.PROPERTY_OUTPUT_SAMPLE_RATE);
            if (rateStr != null) {
                try {
                    int rate = Integer.parseInt(rateStr);
                    if (rate == 44100 || rate == 48000) return rate;
                } catch (NumberFormatException ignored) {}
            }
        }
        return 48000;
    }

    private int getOptimalFramesPerBuffer() {
        AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        if (am != null) {
            String fpbStr = am.getProperty(AudioManager.PROPERTY_OUTPUT_FRAMES_PER_BUFFER);
            if (fpbStr != null) {
                try {
                    int fpb = Integer.parseInt(fpbStr);
                    if (fpb >= 64 && fpb <= 512) return fpb;
                } catch (NumberFormatException ignored) {}
            }
        }
        return 192;
    }

    private AudioDeviceInfo findBuiltInMic() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            if (am != null) {
                for (AudioDeviceInfo dev : am.getDevices(AudioManager.GET_DEVICES_INPUTS)) {
                    if (dev.getType() == AudioDeviceInfo.TYPE_BUILTIN_MIC) return dev;
                }
            }
        }
        return null;
    }

    /**
     * Zero-allocation Real-time DSP Chain:
     * 1. LR24 High-Pass Filter (2 cascaded 12dB/oct Butterworth biquads @ 90Hz)
     * 2. dBFS Noise Gate (-55 to -20 dBFS)
     * 3. SSB Frequency Shifter (+4Hz anti-howling) + 2.4kHz Notch
     * 4. 3:1 Vocal Compressor + -2.0 dBFS Ceiling Limiter
     * 5. 3-Band Vocal EQ + Echo + Schroeder Reverb
     */
    private void processAudioLoop(int sampleRate, int frameSamples) {
        Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_AUDIO);

        // Pre-allocated buffers (zero GC allocation inside while loop)
        final short[] inBuf = new short[frameSamples];
        final short[] outStereoBuf = new short[frameSamples * 2];
        final byte[] recBytesBuf = new byte[frameSamples * 4];

        // 1. LR24 HPF Biquad Coefficients (2 cascaded 2nd-order Butterworth stages @ 90Hz)
        double hpfW0 = 2.0 * Math.PI * hpfCutoffHz / sampleRate;
        double hpfCos = Math.cos(hpfW0);
        double hpfAlpha = Math.sin(hpfW0) / Math.sqrt(2.0); // Q = 0.7071
        double hA0 = 1.0 + hpfAlpha;
        double hb0 = ((1.0 + hpfCos) * 0.5) / hA0;
        double hb1 = (-(1.0 + hpfCos)) / hA0;
        double hb2 = hb0;
        double ha1 = (-2.0 * hpfCos) / hA0;
        double ha2 = (1.0 - hpfAlpha) / hA0;
        double h1x1 = 0, h1x2 = 0, h1y1 = 0, h1y2 = 0;
        double h2x1 = 0, h2x2 = 0, h2y1 = 0, h2y2 = 0;

        // 2. Hilbert Transform 90-deg All-Pass IIR Network for SSB Frequency Shifter (+4Hz)
        // Two parallel all-pass chains maintaining ~90 deg phase difference across 200Hz-6kHz
        final double[] apA = { 0.6923878, 0.9360654322959, 0.9882295226860, 0.9987488452737 };
        final double[] apB = { 0.4021921162426, 0.8561710882420, 0.9722909545651, 0.9952884791278 };
        final double[] sA1 = new double[4], sA2 = new double[4];
        final double[] sB1 = new double[4], sB2 = new double[4];
        double shiftPhase = 0.0;
        final double shiftPhaseInc = 2.0 * Math.PI * freqShiftHz / sampleRate;

        // 3. Anti-Howling Notch Filter (2.4kHz)
        double nw0 = 2.0 * Math.PI * 2400.0 / sampleRate;
        double nAlpha = Math.sin(nw0) / (2.0 * 4.5);
        double nb0 = 1.0 / (1.0 + nAlpha);
        double nb1 = (-2.0 * Math.cos(nw0)) / (1.0 + nAlpha);
        double nb2 = 1.0 / (1.0 + nAlpha);
        double na1 = nb1, na2 = (1.0 - nAlpha) / (1.0 + nAlpha);
        double nx1 = 0, nx2 = 0, ny1 = 0, ny2 = 0;

        // 4. 3-Band EQ states
        float lpBassAlpha = (float) (2.0 * Math.PI * 220.0 / (sampleRate + 2.0 * Math.PI * 220.0));
        float lpMidAlpha = (float) (2.0 * Math.PI * 2800.0 / (sampleRate + 2.0 * Math.PI * 2800.0));
        float eqBassLp = 0f, eqMidLp = 0f;

        // 5. Echo & Schroeder Reverb buffers
        int maxEchoSamples = (int) (sampleRate * 0.5f);
        float[] echoBuf = new float[maxEchoSamples];
        int echoIdx = 0;
        float echoLpState = 0f;

        int[] combLengths = {
            (int)(0.0297f * sampleRate),
            (int)(0.0371f * sampleRate),
            (int)(0.0411f * sampleRate),
            (int)(0.0437f * sampleRate)
        };
        float[][] combBufs = new float[4][];
        int[] combIdx = new int[4];
        float[] combLp = new float[4];
        for (int c = 0; c < 4; c++) combBufs[c] = new float[combLengths[c]];

        int[] apLengths = { (int)(0.0050f * sampleRate), (int)(0.0017f * sampleRate) };
        float[][] apBufs = new float[2][];
        int[] apIdx = new int[2];
        for (int a = 0; a < 2; a++) apBufs[a] = new float[apLengths[a]];

        float gateEnv = 0f;
        float gateGain = 1.0f;
        float compEnv = 0f;
        final float limiterCeiling = 0.7943f; // -2.0 dBFS hard protection ceiling

        try {
            audioTrack.write(outStereoBuf, 0, frameSamples * 2);
            audioTrack.play();
            audioRecord.startRecording();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                while (audioRecord.read(inBuf, 0, frameSamples, AudioRecord.READ_NON_BLOCKING) > 0) {
                    // Flush stale startup frames
                }
            }

            long lastMeterTime = 0;

            while (isRunning) {
                int read = audioRecord.read(inBuf, 0, frameSamples);
                if (read <= 0) continue;

                float sumSq = 0f;
                int echoDelaySamples = Math.min(maxEchoSamples - 1, Math.max(1, (int) (echoDelayMs * sampleRate / 1000.0f)));
                float curGain = micGain;
                float curDry = dryLevel;
                float curEchoMix = echoMix;
                float curEchoFb = echoFeedback;
                float curRevMix = reverbMix;
                float curRevDecay = reverbDecay;
                float gateThreshLin = (float) Math.pow(10.0, gateThresholdDb / 20.0);
                float bassMul = (float) Math.pow(10.0, bassDb / 20.0);
                float midMul = (float) Math.pow(10.0, midDb / 20.0);
                float trebleMul = (float) Math.pow(10.0, trebleDb / 20.0);
                boolean useHpf = lowCutEnabled;
                boolean useShift = freqShiftEnabled;
                boolean useNotch = antiHowlNotch;

                for (int i = 0; i < read; i++) {
                    float x = inBuf[i] / 32768.0f;

                    // [STEP 1] LR24 High-Pass Filter (24dB/oct @ 90Hz)
                    if (useHpf) {
                        double y1 = hb0 * x + hb1 * h1x1 + hb2 * h1x2 - ha1 * h1y1 - ha2 * h1y2;
                        h1x2 = h1x1; h1x1 = x; h1y2 = h1y1; h1y1 = y1;
                        double y2 = hb0 * y1 + hb1 * h2x1 + hb2 * h2x2 - ha1 * h2y1 - ha2 * h2y2;
                        h2x2 = h2x1; h2x1 = y1; h2y2 = h2y1; h2y1 = y2;
                        x = (float) y2;
                    }

                    // [STEP 2] Noise Gate (-55 to -20 dBFS)
                    float absX = Math.abs(x);
                    gateEnv = (absX > gateEnv) ? (gateEnv * 0.72f + absX * 0.28f) : (gateEnv * 0.9994f + absX * 0.0006f);
                    float targetGate = (gateEnv >= gateThreshLin) ? 1.0f : 0.002f;
                    float gateCoeff = (targetGate > gateGain) ? 0.12f : 0.006f;
                    gateGain = gateGain + gateCoeff * (targetGate - gateGain);
                    x *= gateGain;

                    // [STEP 3] Feedback Suppressor: SSB Frequency Shifter (+4Hz) + Dynamic Notch
                    if (useShift) {
                        double sigI = x;
                        double sigQ = x;
                        for (int k = 0; k < 4; k++) {
                            double tmpI = apA[k] * (sigI - sA2[k]) + sA1[k];
                            sA1[k] = sigI; sA2[k] = tmpI; sigI = tmpI;

                            double tmpQ = apB[k] * (sigQ - sB2[k]) + sB1[k];
                            sB1[k] = sigQ; sB2[k] = tmpQ; sigQ = tmpQ;
                        }
                        x = (float) (sigI * Math.cos(shiftPhase) - sigQ * Math.sin(shiftPhase));
                        shiftPhase += shiftPhaseInc;
                        if (shiftPhase > 2.0 * Math.PI) shiftPhase -= 2.0 * Math.PI;
                    }
                    if (useNotch) {
                        double ny = nb0 * x + nb1 * nx1 + nb2 * nx2 - na1 * ny1 - na2 * ny2;
                        nx2 = nx1; nx1 = x; ny2 = ny1; ny1 = ny;
                        x = (float) ny;
                    }

                    // 3-Band Vocal EQ
                    eqBassLp += lpBassAlpha * (x - eqBassLp);
                    eqMidLp += lpMidAlpha * (x - eqMidLp);
                    x = eqBassLp * bassMul + (eqMidLp - eqBassLp) * midMul + (x - eqMidLp) * trebleMul;

                    // [STEP 4] Mic Gain + 3:1 Compressor
                    float voice = x * curGain;
                    float vAbs = Math.abs(voice);
                    compEnv = (vAbs > compEnv) ? (compEnv * 0.90f + vAbs * 0.10f) : (compEnv * 0.9990f + vAbs * 0.0010f);
                    float compGain = 1.15f;
                    if (compEnv > 0.20f) { // -14 dBFS threshold, 3:1 ratio
                        float targetLvl = 0.20f + (compEnv - 0.20f) * 0.3333f;
                        compGain *= (targetLvl / compEnv);
                    }
                    voice *= compGain;
                    sumSq += voice * voice;

                    // Echo & Reverb
                    int readEchoIdx = echoIdx - echoDelaySamples;
                    if (readEchoIdx < 0) readEchoIdx += maxEchoSamples;
                    float delayed = echoBuf[readEchoIdx];
                    echoLpState = echoLpState * 0.55f + delayed * 0.45f;
                    echoBuf[echoIdx] = voice + echoLpState * curEchoFb;
                    echoIdx++;
                    if (echoIdx >= maxEchoSamples) echoIdx = 0;

                    float revSum = 0f;
                    for (int c = 0; c < 4; c++) {
                        int idx = combIdx[c];
                        float combOut = combBufs[c][idx];
                        combLp[c] = combLp[c] * 0.35f + combOut * 0.65f;
                        combBufs[c][idx] = voice * 0.06f + combLp[c] * curRevDecay;
                        idx++;
                        if (idx >= combLengths[c]) idx = 0;
                        combIdx[c] = idx;
                        revSum += combOut;
                    }
                    float apSig = revSum;
                    for (int a = 0; a < 2; a++) {
                        int idx = apIdx[a];
                        float bufOut = apBufs[a][idx];
                        float apIn = apSig + bufOut * 0.5f;
                        apBufs[a][idx] = apIn;
                        apSig = bufOut - apIn * 0.5f;
                        idx++;
                        if (idx >= apLengths[a]) idx = 0;
                        apIdx[a] = idx;
                    }

                    // Mix & -2.0 dBFS Limiter (0.7943f ceiling)
                    float mixed = voice * curDry + delayed * curEchoMix + apSig * curRevMix;
                    if (mixed > limiterCeiling) {
                        float over = mixed - limiterCeiling;
                        mixed = limiterCeiling + (over / (1.0f + over * 8.0f)) * 0.10f;
                    } else if (mixed < -limiterCeiling) {
                        float over = -mixed - limiterCeiling;
                        mixed = -(limiterCeiling + (over / (1.0f + over * 8.0f)) * 0.10f);
                    }

                    int outSample = (int) (mixed * 32767.0f);
                    if (outSample > 32767) outSample = 32767; else if (outSample < -32768) outSample = -32768;
                    short s = (short) outSample;
                    outStereoBuf[i * 2] = s;
                    outStereoBuf[i * 2 + 1] = s;

                    if (isRecordingWav) {
                        int bIdx = i * 4;
                        recBytesBuf[bIdx] = (byte) (s & 0xff);
                        recBytesBuf[bIdx + 1] = (byte) ((s >> 8) & 0xff);
                        recBytesBuf[bIdx + 2] = recBytesBuf[bIdx];
                        recBytesBuf[bIdx + 3] = recBytesBuf[bIdx + 1];
                    }
                }

                audioTrack.write(outStereoBuf, 0, read * 2);

                if (isRecordingWav) {
                    synchronized (recLock) {
                        if (isRecordingWav && wavOutStream != null) {
                            try {
                                int byteCount = read * 4;
                                wavOutStream.write(recBytesBuf, 0, byteCount);
                                wavDataBytes += byteCount;
                            } catch (Exception ignored) {}
                        }
                    }
                }

                float rms = (float) Math.sqrt(sumSq / read);
                currentDb = rms > 0.0001f ? (float) (20.0 * Math.log10(rms)) : -80.0f;

                long now = System.currentTimeMillis();
                if (meterCallback != null && now - lastMeterTime > 75) {
                    lastMeterTime = now;
                    meterCallback.onMeterUpdate(currentDb, estimatedLatencyMs);
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Audio loop error", e);
        } finally {
            releaseResources();
        }
    }
}
