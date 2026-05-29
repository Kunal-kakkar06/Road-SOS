import { useRef, useState, useEffect } from 'react';

export default function PhotoCapture({ onCapture, captured, onClear }) {
  const galleryInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState('');

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (file) onCapture(file);
  };

  // Start in-app camera
  const startCamera = async () => {
    setCameraError('');
    setIsCameraActive(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error('Camera access error:', err);
      setCameraError('Could not access camera. Please check permissions or use Upload.');
      setIsCameraActive(false);
    }
  };

  // Stop camera stream
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  };

  // Capture frame from video to canvas
  const capturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], `live_photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
          onCapture(file);
          stopCamera();
        }
      }, 'image/jpeg', 0.85);
    }
  };

  // Clean up stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  if (captured) {
    const url = URL.createObjectURL(captured);
    return (
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <div style={{
          width: 80, height: 80, borderRadius: 8,
          overflow: 'hidden', flexShrink: 0,
          border: '2px solid #27AE60',
        }}>
          <img
            src={url}
            alt="Injury"
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: '#27AE60', margin: '0 0 3px' }}>
            ✓ Photo captured
          </p>
          <p style={{
            fontSize: 11, color: '#534433', margin: '0 0 8px',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            maxWidth: 180,
          }}>
            {captured.name}
          </p>
          <button
            onClick={onClear}
            style={{
              fontSize: 12, color: '#ba1a1a', background: 'none',
              border: 'none', cursor: 'pointer', padding: 0,
              fontFamily: 'Inter, sans-serif', fontWeight: 600,
            }}
          >
            Remove photo
          </button>
        </div>
      </div>
    );
  }

  if (isCameraActive) {
    return (
      <div style={{
        background: '#000',
        borderRadius: 10,
        overflow: 'hidden',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '10px 0 16px',
      }}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          style={{
            width: '100%',
            maxHeight: 240,
            objectFit: 'cover',
            background: '#1a1a1a',
          }}
        />
        <div style={{ display: 'flex', gap: 12, marginTop: 12, justifyContent: 'center', width: '100%' }}>
          <button
            onClick={capturePhoto}
            style={{
              background: '#006687',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: 20,
              fontWeight: 600,
              fontSize: 13,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>photo_camera</span>
            Capture
          </button>
          <button
            onClick={stopCamera}
            style={{
              background: '#ba1a1a',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: 20,
              fontWeight: 600,
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {/* Option 1: Live Photo */}
        <div
          onClick={startCamera}
          style={{
            border: '2px dashed #d9c3ad',
            borderRadius: 10,
            padding: '16px 8px',
            textAlign: 'center',
            cursor: 'pointer',
            background: '#fff8f4',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = '#14213D';
            e.currentTarget.style.background = '#fff';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = '#d9c3ad';
            e.currentTarget.style.background = '#fff8f4';
          }}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 28, color: '#006687', display: 'block', marginBottom: 6 }}
          >
            photo_camera
          </span>
          <p style={{ fontSize: 12, color: '#14213D', margin: '0 0 2px', fontWeight: 600 }}>
            Take Live Photo
          </p>
          <p style={{ fontSize: 10, color: '#867461', margin: 0 }}>
            Use device camera
          </p>
        </div>

        {/* Option 2: Upload from Gallery */}
        <div
          onClick={() => galleryInputRef.current?.click()}
          style={{
            border: '2px dashed #d9c3ad',
            borderRadius: 10,
            padding: '16px 8px',
            textAlign: 'center',
            cursor: 'pointer',
            background: '#fff8f4',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = '#14213D';
            e.currentTarget.style.background = '#fff';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = '#d9c3ad';
            e.currentTarget.style.background = '#fff8f4';
          }}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 28, color: '#006687', display: 'block', marginBottom: 6 }}
          >
            upload_file
          </span>
          <p style={{ fontSize: 12, color: '#14213D', margin: '0 0 2px', fontWeight: 600 }}>
            Upload Image
          </p>
          <p style={{ fontSize: 10, color: '#867461', margin: 0 }}>
            Choose from gallery
          </p>
        </div>
      </div>

      {cameraError && (
        <p style={{ fontSize: 11, color: '#ba1a1a', marginTop: 8, textAlign: 'center', fontWeight: 500 }}>
          {cameraError}
        </p>
      )}

      {/* Hidden gallery input */}
      <input
        ref={galleryInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFile}
      />
    </div>
  );
}

