// Browser-based audio conversion utilities

export async function convertWebMToWAV(webmBlob: Blob): Promise<Blob> {
  // Create an audio context
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  
  try {
    // Convert blob to ArrayBuffer
    const arrayBuffer = await webmBlob.arrayBuffer();
    
    // Decode audio data
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    
    // Get audio data
    const numberOfChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const length = audioBuffer.length;
    
    // Create WAV file
    const wavBuffer = encodeWAV(audioBuffer, sampleRate);
    
    // Create blob
    return new Blob([wavBuffer], { type: 'audio/wav' });
  } finally {
    audioContext.close();
  }
}

function encodeWAV(audioBuffer: AudioBuffer, sampleRate: number): ArrayBuffer {
  const numberOfChannels = audioBuffer.numberOfChannels;
  const length = audioBuffer.length;
  const bitsPerSample = 16;
  const bytesPerSample = bitsPerSample / 8;
  const blockAlign = numberOfChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = length * blockAlign;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  
  // WAV header
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };
  
  // RIFF chunk descriptor
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, 'WAVE');
  
  // fmt sub-chunk
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // audio format (1 = PCM)
  view.setUint16(22, numberOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  
  // data sub-chunk
  writeString(36, 'data');
  view.setUint32(40, dataSize, true);
  
  // Write audio data
  let offset = 44;
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numberOfChannels; channel++) {
      const sample = audioBuffer.getChannelData(channel)[i];
      // Convert float to 16-bit PCM
      const s = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      offset += 2;
    }
  }
  
  return buffer;
}

// Alternative: Use RecordRTC library for more format options
export function isBrowserConversionSupported(): boolean {
  return !!(window.AudioContext || (window as any).webkitAudioContext);
}

// Simple OGG recording using native browser APIs (if supported)
export function canRecordOGG(): boolean {
  return MediaRecorder.isTypeSupported('audio/ogg;codecs=opus') || 
         MediaRecorder.isTypeSupported('audio/ogg');
}

// Get the best supported format that Gemma accepts
export function getBestSupportedFormat(): { mimeType: string; extension: string } {
  // Formats directly supported by Gemma API
  const gemmaFormats = [
    { mimeType: 'audio/wav', extension: 'wav' },
    { mimeType: 'audio/mp3', extension: 'mp3' },
    { mimeType: 'audio/flac', extension: 'flac' },
    { mimeType: 'audio/mp4', extension: 'm4a' },
    { mimeType: 'audio/mp4;codecs=mp4a.40.2', extension: 'm4a' },
    { mimeType: 'audio/ogg;codecs=opus', extension: 'ogg' },
    { mimeType: 'audio/ogg', extension: 'ogg' }
  ];
  
  for (const format of gemmaFormats) {
    if (MediaRecorder.isTypeSupported(format.mimeType)) {
      return format;
    }
  }
  
  // Default to WebM (will need conversion)
  return { mimeType: 'audio/webm', extension: 'webm' };
}

// Convert to MP4/AAC using MediaRecorder if supported
export async function tryNativeMP4Recording(stream: MediaStream): Promise<MediaRecorder | null> {
  const mp4Formats = [
    'audio/mp4',
    'audio/mp4;codecs=mp4a.40.2', // AAC-LC
    'audio/aac',
    'audio/mpeg'
  ];
  
  for (const format of mp4Formats) {
    if (MediaRecorder.isTypeSupported(format)) {
      try {
        return new MediaRecorder(stream, { 
          mimeType: format,
          audioBitsPerSecond: 128000 
        });
      } catch (e) {
        console.warn(`Failed to create recorder with ${format}:`, e);
      }
    }
  }
  
  return null;
}