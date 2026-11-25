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
 * Ansound Native Low-Latency Android Karaoke Audio Engine.
 * Features:
 * - Native Stereo FastMixer output (CHANNEL_OUT_STEREO) eliminating mono-resampler crackling
 * - 3-Band Vocal EQ (Bass 180Hz, Mid 1.2kHz, Treble 5kHz)
 * - 3D Stereo Doubler / Chorus (Hát bè đôi)
 * - Damped Echo + Headroom-safe Schroeder Reverb + Soft Limiter
 * - Hardware AEC/NS + Near-Field Gate
 * - Live 16-bit Stereo WAV Recorder
 */
public class NativeKaraokeEngine {
    private static final String TAG = "NativeKaraokeEngine";

    private final Context context;
    private volatile boolean isRunning = false;
    private Thread audioThread;

    private AudioRecord audioRecord;
    private AudioTrack audioTrack;
    private AcousticEchoCanceler aec;
    private NoiseSuppressor ns;
    private AutomaticGainControl agc;

    // Live DSP parameters (thread-safe volatile)
    private volatile float micGain = 1.15f;         // 0.0 - 4.0
    private volatile float dryLevel = 1.00f;        // 0.0 - 1.0
    private volatile float echoMix = 0.15f;         // 0.0 - 1.0
    private volatile int echoDelayMs = 180;         // 80 - 400 ms
    private volatile float echoFeedback = 0.25f;    // 0.0 - 0.75
    private volatile float reverbMix = 0.15f;       // 0.0 - 1.0
    private volatile float reverbDecay = 0.68f;     // 0.3 - 0.90
    private volatile float bassDb = 1.0f;           // -9.0 - +9.0 dB (180Hz)
    private volatile float midDb = 1.0f;            // -9.0 - +9.0 dB (1.2kHz)
    private volatile float trebleDb = 1.5f;         // -9.0 - +9.0 dB (5kHz)
    private volatile float stereoChorus = 0.0f;     // 0.0 - 1.0 (Off by default for pure vocal clarity)
    private volatile float nearFieldLevel = 0.20f;  // 0.0 - 1.0 (Gentle gate so words are never chopped)
    private volatile boolean lowCutEnabled = true;
    private volatile boolean antiHowlEnabled = true;
    private volatile boolean hwAecEnabled = false;  // Off by default for StarMaker Direct Low-Latency FastCapture path

    private volatile float currentDb = -80.0f;
    private volatile int activeSampleRate = 48000;

    // Live WAV Recording state
    private volatile boolean isRecordingWav = false;
    private BufferedOutputStream wavOutStream;
    private File wavFile;
    private long wavDataBytes = 0;
    private final Object recLock = new Object();

    public interface MeterCallback {
        void onMeterUpdate(float db);
    }

    private MeterCallback meterCallback;

    public NativeKaraokeEngine(Context context) {
        this.context = context.getApplicationContext();
    }

    public void setMeterCallback(MeterCallback callback) {
        this.meterCallback = callback;
    }

    public boolean isRunning() {
        return isRunning;
    }

    public boolean isRecordingWav() {
        return isRecordingWav;
    }

    public float getCurrentDb() {
        return currentDb;
    }

    // Parameter setters
    public void setMicGain(float gain) { this.micGain = Math.max(0f, Math.min(4.0f, gain)); }
    public void setDryLevel(float level) { this.dryLevel = Math.max(0f, Math.min(1.0f, level)); }
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
    public void setNearFieldLevel(float level) { this.nearFieldLevel = Math.max(0f, Math.min(1f, level)); }
    public void setLowCutEnabled(boolean enabled) { this.lowCutEnabled = enabled; }
    public void setAntiHowlEnabled(boolean enabled) { this.antiHowlEnabled = enabled; }
    public void setHwAecEnabled(boolean enabled) {
        this.hwAecEnabled = enabled;
        if (aec != null) {
            try { aec.setEnabled(enabled); } catch (Exception ignored) {}
        }
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
                // Write 44-byte placeholder WAV header
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
        header[20] = 1; header[21] = 0; // PCM
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

        final int burstFrames = getOptimalFramesPerBuffer();
        final int frameSamples = Math.max(256, burstFrames * 2);
        final int recBufBytes = Math.max(minInBuf, frameSamples * 2 * 2);
        final int playBufBytes = Math.max(minOutBuf, frameSamples * 4 * 2);

        try {
            audioRecord = new AudioRecord(
                    MediaRecorder.AudioSource.MIC,
                    sampleRate,
                    channelIn,
                    encoding,
                    recBufBytes
            );

            if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord failed to initialize");
                releaseResources();
                return false;
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                AudioDeviceInfo builtInMic = findBuiltInMic();
                if (builtInMic != null) {
                    audioRecord.setPreferredDevice(builtInMic);
                }
            }

            int sessionId = audioRecord.getAudioSessionId();
            if (hwAecEnabled) {
                if (AcousticEchoCanceler.isAvailable()) {
                    aec = AcousticEchoCanceler.create(sessionId);
                    if (aec != null) aec.setEnabled(true);
                }
                if (NoiseSuppressor.isAvailable()) {
                    ns = NoiseSuppressor.create(sessionId);
                    if (ns != null) ns.setEnabled(true);
                }
            }
            if (AutomaticGainControl.isAvailable()) {
                agc = AutomaticGainControl.create(sessionId);
                if (agc != null) {
                    agc.setEnabled(false);
                }
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

            isRunning = true;
            final int finalSampleRate = sampleRate;
            audioThread = new Thread(() -> processAudioLoop(finalSampleRate, frameSamples), "KaraokeDspThread");
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

    public synchronized void stop() {
        stopWavRecording();
        isRunning = false;
        if (audioThread != null) {
            try {
                audioThread.join(400);
            } catch (InterruptedException ignored) {}
            audioThread = null;
        }
        releaseResources();
        currentDb = -80.0f;
    }

    private void releaseResources() {
        if (aec != null) {
            try { aec.release(); } catch (Exception ignored) {}
            aec = null;
        }
        if (ns != null) {
            try { ns.release(); } catch (Exception ignored) {}
            ns = null;
        }
        if (agc != null) {
            try { agc.release(); } catch (Exception ignored) {}
            agc = null;
        }
        if (audioRecord != null) {
            try {
                if (audioRecord.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                    audioRecord.stop();
                }
                audioRecord.release();
            } catch (Exception ignored) {}
            audioRecord = null;
        }
        if (audioTrack != null) {
            try {
                if (audioTrack.getPlayState() == AudioTrack.PLAYSTATE_PLAYING) {
                    audioTrack.stop();
                }
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
                    if (fpb >= 64 && fpb <= 1024) return fpb;
                } catch (NumberFormatException ignored) {}
            }
        }
        return 192;
    }

    private AudioDeviceInfo findBuiltInMic() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            AudioManager am = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            if (am != null) {
                AudioDeviceInfo[] inputs = am.getDevices(AudioManager.GET_DEVICES_INPUTS);
                for (AudioDeviceInfo dev : inputs) {
                    if (dev.getType() == AudioDeviceInfo.TYPE_BUILTIN_MIC) {
                        return dev;
                    }
                }
            }
        }
        return null;
    }

    private void processAudioLoop(int sampleRate, int frameSamples) {
        Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_AUDIO);

        short[] inBuf = new short[frameSamples];
        short[] outStereoBuf = new short[frameSamples * 2];
        byte[] recBytesBuf = new byte[frameSamples * 4];

        // 1. Echo circular buffer (up to 500ms)
        int maxEchoSamples = (int) (sampleRate * 0.5f);
        float[] echoBuf = new float[maxEchoSamples];
        int echoIdx = 0;
        float echoLpState = 0f;

        // 2. 3D Stereo Doubler / Haas Chorus buffer (~14ms)
        int chorusDelaySamples = (int) (0.014f * sampleRate);
        float[] chorusBuf = new float[chorusDelaySamples + 16];
        int chorusIdx = 0;

        // 3. Schroeder Reverb
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

        int[] apLengths = {
            (int)(0.0050f * sampleRate),
            (int)(0.0017f * sampleRate)
        };
        float[][] apBufs = new float[2][];
        int[] apIdx = new int[2];
        for (int a = 0; a < 2; a++) apBufs[a] = new float[apLengths[a]];

        // 4. Filter states: 100Hz High-Pass & 6.8kHz De-Hisser Low-Pass
        float hpfAlpha = (float) (1.0 / (1.0 + (2.0 * Math.PI * 100.0 / sampleRate)));
        float hpfPrevIn = 0f, hpfPrevOut = 0f;
        float deHissAlpha = (float) (2.0 * Math.PI * 6800.0 / (sampleRate + 2.0 * Math.PI * 6800.0));
        float deHissState = 0f;

        // 3-Band Crossover-style Vocal EQ states (Bass 180Hz, Mid 1.2kHz, Treble 5kHz)
        float lpBassAlpha = (float) (2.0 * Math.PI * 220.0 / (sampleRate + 2.0 * Math.PI * 220.0));
        float lpMidAlpha = (float) (2.0 * Math.PI * 2800.0 / (sampleRate + 2.0 * Math.PI * 2800.0));
        float eqBassLp = 0f, eqMidLp = 0f;

        // Anti-Howling Notch Filter (2.4kHz)
        double w0 = 2.0 * Math.PI * 2400.0 / sampleRate;
        double Q = 4.5;
        double alpha = Math.sin(w0) / (2.0 * Q);
        double b0 = 1.0 / (1.0 + alpha);
        double b1 = (-2.0 * Math.cos(w0)) / (1.0 + alpha);
        double b2 = 1.0 / (1.0 + alpha);
        double a1 = b1;
        double a2 = (1.0 - alpha) / (1.0 + alpha);
        double nx1 = 0, nx2 = 0, ny1 = 0, ny2 = 0;

        float gateEnv = 0f;
        float gateGain = 1.0f;
        float compEnv = 0f;

        try {
            // Start playback engine first so record doesn't accumulate backlog during track startup
            audioTrack.write(outStereoBuf, 0, frameSamples * 2);
            audioTrack.play();
            audioRecord.startRecording();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                while (audioRecord.read(inBuf, 0, frameSamples, AudioRecord.READ_NON_BLOCKING) > 0) {
                    // discard startup buffer
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
                float curChorus = stereoChorus;
                float bassMul = (float) Math.pow(10.0, bassDb / 20.0);
                float midMul = (float) Math.pow(10.0, midDb / 20.0);
                float trebleMul = (float) Math.pow(10.0, trebleDb / 20.0);
                boolean useHpf = lowCutEnabled;
                boolean useNotch = antiHowlEnabled;
                float gateThreshold = 0.001f + nearFieldLevel * 0.029f;

                for (int i = 0; i < read; i++) {
                    float x = inBuf[i] / 32768.0f;

                    if (useHpf) {
                        float y = hpfAlpha * (hpfPrevOut + x - hpfPrevIn);
                        hpfPrevIn = x;
                        hpfPrevOut = y;
                        x = y;
                    }

                    // 6.8kHz De-Hisser LPF removes high-frequency mic self-noise & air hiss
                    deHissState += deHissAlpha * (x - deHissState);
                    x = deHissState;

                    if (useNotch) {
                        double ny = b0 * x + b1 * nx1 + b2 * nx2 - a1 * ny1 - a2 * ny2;
                        nx2 = nx1; nx1 = x;
                        ny2 = ny1; ny1 = ny;
                        x = (float) ny;
                    }

                    float absX = Math.abs(x);
                    if (absX > gateEnv) gateEnv = gateEnv * 0.70f + absX * 0.30f;
                    else gateEnv = gateEnv * 0.9994f + absX * 0.0006f;

                    float targetGate;
                    if (gateThreshold <= 0.0015f || gateEnv >= gateThreshold) {
                        targetGate = 1.0f;
                    } else {
                        float ratio = gateEnv / gateThreshold;
                        // Deep -60dB silence floor below threshold eliminates background hiss & fan noise
                        targetGate = 0.001f + 0.999f * (ratio * ratio * ratio);
                    }
                    float gateCoeff = (targetGate > gateGain) ? 0.08f : 0.006f;
                    gateGain = gateGain + gateCoeff * (targetGate - gateGain);
                    x *= gateGain;

                    // 3-Band Vocal EQ (Bass < 220Hz, Mid 220-2800Hz, Treble > 2800Hz)
                    eqBassLp += lpBassAlpha * (x - eqBassLp);
                    eqMidLp += lpMidAlpha * (x - eqMidLp);
                    float lowBand = eqBassLp;
                    float midBand = eqMidLp - eqBassLp;
                    float highBand = x - eqMidLp;
                    x = lowBand * bassMul + midBand * midMul + highBand * trebleMul;

                    float voice = x * curGain;

                    // Broadcast Vocal Compressor + Makeup Gain (balances voice loudness against mastered YouTube music)
                    float vAbs = Math.abs(voice);
                    compEnv = (vAbs > compEnv) ? (compEnv * 0.92f + vAbs * 0.08f) : (compEnv * 0.9992f + vAbs * 0.0008f);
                    float compGain = 1.20f; // Gentle vocal makeup boost without triggering speaker feedback
                    if (compEnv > 0.25f) {
                        // Smooth 4:1 compression above -12dBFS so voice stays loud & punchy without clipping
                        float targetLevel = 0.25f + (compEnv - 0.25f) * 0.25f;
                        compGain *= (targetLevel / compEnv);
                    }
                    voice *= compGain;

                    sumSq += voice * voice;

                    // Echo Delay Loop
                    int readEchoIdx = echoIdx - echoDelaySamples;
                    if (readEchoIdx < 0) readEchoIdx += maxEchoSamples;
                    float delayed = echoBuf[readEchoIdx];
                    echoLpState = echoLpState * 0.55f + delayed * 0.45f;
                    echoBuf[echoIdx] = voice + echoLpState * curEchoFb;
                    echoIdx++;
                    if (echoIdx >= maxEchoSamples) echoIdx = 0;

                    // Schroeder Reverb
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

                    // 3D Stereo Doubler (Haas effect: L gets direct, R gets +14ms micro-doubled voice)
                    int readChorusIdx = chorusIdx - chorusDelaySamples;
                    if (readChorusIdx < 0) readChorusIdx += chorusBuf.length;
                    float doubled = chorusBuf[readChorusIdx];
                    chorusBuf[chorusIdx] = voice;
                    chorusIdx++;
                    if (chorusIdx >= chorusBuf.length) chorusIdx = 0;

                    float baseFx = delayed * curEchoMix + apSig * curRevMix;
                    float mixedL = voice * curDry + baseFx + doubled * (curChorus * 0.22f);
                    float mixedR = voice * curDry + baseFx + doubled * (curChorus * 0.14f);

                    // Soft-limiter L/R
                    mixedL = softLimit(mixedL);
                    mixedR = softLimit(mixedR);

                    int outL = (int) (mixedL * 32767.0f);
                    int outR = (int) (mixedR * 32767.0f);
                    if (outL > 32767) outL = 32767; else if (outL < -32768) outL = -32768;
                    if (outR > 32767) outR = 32767; else if (outR < -32768) outR = -32768;

                    short sL = (short) outL;
                    short sR = (short) outR;
                    outStereoBuf[i * 2] = sL;
                    outStereoBuf[i * 2 + 1] = sR;

                    if (isRecordingWav) {
                        int bIdx = i * 4;
                        recBytesBuf[bIdx] = (byte) (sL & 0xff);
                        recBytesBuf[bIdx + 1] = (byte) ((sL >> 8) & 0xff);
                        recBytesBuf[bIdx + 2] = (byte) (sR & 0xff);
                        recBytesBuf[bIdx + 3] = (byte) ((sR >> 8) & 0xff);
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
                    meterCallback.onMeterUpdate(currentDb);
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Audio loop error", e);
        } finally {
            releaseResources();
        }
    }

    private float softLimit(float v) {
        if (v > 0.85f) {
            float over = v - 0.85f;
            return 0.85f + (over / (1.0f + over * 6.66f)) * 0.14f;
        } else if (v < -0.85f) {
            float over = -v - 0.85f;
            return -(0.85f + (over / (1.0f + over * 6.66f)) * 0.14f);
        }
        return v;
    }
}
