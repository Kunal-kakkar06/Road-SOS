import React, { useState, useRef } from 'react';
import { uploadIncidentPhotos } from '../services/incidentService';

export default function PhotoUploader({ incidentId, existingPhotos = [], onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  
  // Webcam capture states
  const [showWebcam, setShowWebcam] = useState(false);
  
  const docInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const handleDocChange = async (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await uploadFiles(Array.from(e.target.files));
    }
  };

  const triggerDocInput = () => {
    docInputRef.current.click();
  };

  // WebRTC Webcam controllers
  const startCamera = async () => {
    setError(null);
    setShowWebcam(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Camera access failed:", err);
      setError("Could not access camera. Ensure permissions are granted.");
      setShowWebcam(false);
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && streamRef.current) {
      const video = videoRef.current;
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      
      const ctx = canvas.getContext('2d');
      // Mirror canvas if facing front user camera (ideal for desktop testers)
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Stop the camera hardware tracks immediately
      stopCamera();

      canvas.toBlob(async (blob) => {
        if (blob) {
          const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
          await uploadFiles([file]);
        }
      }, 'image/jpeg', 0.95);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setShowWebcam(false);
  };

  const uploadFiles = async (files) => {
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    if (imageFiles.length === 0) {
      setError("Please select image files only.");
      return;
    }

    setUploading(true);
    setError(null);

    const result = await uploadIncidentPhotos(incidentId, imageFiles);
    setUploading(false);

    if (result.error) {
      setError("Failed to upload evidence. Check connection.");
    } else {
      if (onUploadSuccess) {
        onUploadSuccess(result.photos);
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      
      {/* Hidden file input for documents */}
      <input 
        ref={docInputRef}
        type="file" 
        multiple 
        accept="image/*" 
        onChange={handleDocChange} 
        style={{ display: 'none' }}
      />

      {/* Main Container */}
      <div style={{
        display: 'flex', flexDirection: 'column', gap: 12,
        background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: 12,
        padding: '24px 16px', alignItems: 'center', textAlign: 'center', position: 'relative',
        overflow: 'hidden'
      }}>
        
        {!showWebcam && (
          <div style={{
            width: 44, height: 44, borderRadius: '50%',
            background: 'rgba(252, 163, 17, 0.1)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', color: '#fca311', marginBottom: 6
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 24 }}>
              add_a_photo
            </span>
          </div>
        )}

        {/* Live Video Capture Screen */}
        {showWebcam ? (
          <div style={{ width: '100%', maxWidth: '480px', position: 'relative', borderRadius: 12, overflow: 'hidden', background: '#000' }}>
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted
              style={{ width: '100%', display: 'block', transform: 'scaleX(1)' }} 
            />
            {/* Shutter controllers overlay */}
            <div style={{
              position: 'absolute', bottom: 16, left: 0, right: 0,
              display: 'flex', justifyContent: 'center', gap: 20, zIndex: 10
            }}>
              <button
                onClick={capturePhoto}
                style={{
                  width: 52, height: 52, borderRadius: '50%', border: '4px solid #fff',
                  background: '#ba1a1a', cursor: 'pointer', outline: 'none',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.4)', transition: 'transform 0.1s'
                }}
                onMouseDown={e => e.currentTarget.style.transform = 'scale(0.9)'}
                onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
                title="Capture Photo"
              />
              <button
                onClick={stopCamera}
                style={{
                  width: 36, height: 36, borderRadius: '50%', border: 'none',
                  background: 'rgba(255,255,255,0.3)', color: '#fff', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  alignSelf: 'center'
                }}
                title="Cancel"
              >
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>close</span>
              </button>
            </div>
          </div>
        ) : (
          <div>
            <p style={{ margin: '0 0 4px', fontSize: 13.5, fontWeight: 700, color: '#0f172a' }}>
              {uploading ? 'Uploading Evidence...' : 'Submit Crash Evidence'}
            </p>
            <p style={{ margin: 0, fontSize: 11.5, color: '#64748b', lineHeight: 1.4 }}>
              Capture a live photo of the crash scene or upload supporting document files (PNG, JPG).
            </p>
          </div>
        )}

        {uploading ? (
          <div style={{
            width: 24, height: 24,
            border: '2px solid rgba(15,23,42,0.08)',
            borderTop: '2px solid #fca311',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            marginTop: 10
          }} />
        ) : (
          !showWebcam && (
            <div style={{
              display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center', marginTop: 10, width: '100%'
            }}>
              <button
                onClick={startCamera}
                style={{
                  flex: '1 1 150px', maxWidth: '240px', padding: '10px 16px', borderRadius: 8, border: 'none',
                  background: '#14213D', color: '#fff', fontSize: 12.5, fontWeight: 800,
                  cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  boxShadow: '0 2px 6px rgba(15,23,42,0.1)'
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>photo_camera</span>
                Live Camera Capture
              </button>
              <button
                onClick={triggerDocInput}
                style={{
                  flex: '1 1 150px', maxWidth: '240px', padding: '10px 16px', borderRadius: 8,
                  border: '1px solid #cbd5e1', background: '#fff', color: '#0f172a',
                  fontSize: 12.5, fontWeight: 700, cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  transition: 'background 0.2s'
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>upload_file</span>
                Upload Documents
              </button>
            </div>
          )
        )}
      </div>

      {error && (
        <div style={{ color: '#ba1a1a', fontSize: 12, textAlign: 'center', fontWeight: 600 }}>
          {error}
        </div>
      )}

      {/* Preview Grid */}
      {existingPhotos.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <p style={{ 
            fontSize: 11, 
            fontWeight: 800, 
            textTransform: 'uppercase', 
            color: '#64748b', 
            letterSpacing: '0.05em', 
            margin: '0 0 10px'
          }}>
            Uploaded Evidence ({existingPhotos.length})
          </p>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(88px, 1fr))',
            gap: 12
          }}>
            {existingPhotos.map((photo, index) => {
              const url = typeof photo === 'string' ? photo : photo.url;
              const finalUrl = url;
              const name = photo.filename || `Evidence #${index + 1}`;

              return (
                <a 
                  key={index} 
                  href={finalUrl} 
                  target="_blank" 
                  rel="noreferrer" 
                  style={{
                    position: 'relative',
                    aspectRatio: '1',
                    borderRadius: 10,
                    overflow: 'hidden',
                    border: '1px solid rgba(15,23,42,0.08)',
                    background: '#f1f5f9',
                    display: 'block',
                    boxShadow: '0 2px 6px rgba(15,23,42,0.03)',
                    transition: 'transform 0.2s'
                  }}
                  onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.04)'}
                  onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                >
                  <img 
                    src={finalUrl} 
                    alt={name} 
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover'
                    }}
                  />
                </a>
              );
            })}
          </div>
        </div>
      )}
      <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
