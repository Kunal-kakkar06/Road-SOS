const FaceMesh = window.FaceMesh;
const Camera = window.Camera;

const LEFT_EYE  = [362,385,387,263,373,380];
const RIGHT_EYE = [33,160,158,133,153,144];
const EAR_THRESH     = 0.25;
const BLINK_FRAMES   = 3;
const DROWSY_BPM     = 25;
const HEAD_DROP_DEG  = 20;
const WINDOW_MS      = 60000;

let faceMesh=null, isRunning=false, onFatigue=null, activeVideoEl=null;
let frameTimeoutId=null;
const blinkTs=[]; let closedF=0, fatigueScore=0;

function ear(lm,idx){
  const p=idx.map(i=>lm[i]);
  return ((dist(p[1],p[5])+dist(p[2],p[4]))/(2*dist(p[0],p[3])));
}
function dist(a,b){return Math.sqrt((a.x-b.x)**2+(a.y-b.y)**2);}
function headTilt(lm){
  const chin=lm[152],fore=lm[10];
  return Math.atan2(Math.abs(chin.x-fore.x),Math.abs(chin.y-fore.y))*(180/Math.PI);
}

function onResults(results){
  if(!results.multiFaceLandmarks?.length) return;
  const lm=results.multiFaceLandmarks[0];
  const now=Date.now();
  const avgEAR=(ear(lm,LEFT_EYE)+ear(lm,RIGHT_EYE))/2;

  if(avgEAR<EAR_THRESH){ closedF++; }
  else{ if(closedF>=BLINK_FRAMES) blinkTs.push(now); closedF=0; }

  const cutoff=now-WINDOW_MS;
  while(blinkTs.length&&blinkTs[0]<cutoff) blinkTs.shift();
  const bpm=blinkTs.length;
  const tilt=headTilt(lm);

  let score=0;
  if(avgEAR<EAR_THRESH)  score+=30;
  if(bpm>DROWSY_BPM)     score+=25;
  if(bpm<10)             score+=20;
  if(tilt>HEAD_DROP_DEG) score+=25;
  fatigueScore=Math.min(100,score);

  if(onFatigue){
    onFatigue({score:fatigueScore,blinksPerMin:bpm,
               avgEAR:avgEAR.toFixed(3),headTilt:tilt.toFixed(1)});
  }
}

const runLoop = async (videoEl) => {
  if (!isRunning) return;
  try {
    if (videoEl.readyState >= 2) {
      await faceMesh.send({ image: videoEl });
    }
  } catch (_) {}
  
  // Throttle frame processing to 5 FPS (every 200ms) to ensure smooth UI performance
  frameTimeoutId = setTimeout(() => {
    runLoop(videoEl);
  }, 200);
};

export const startFatigueMonitoring = async (videoEl, callback) => {
  if(isRunning) return true;
  onFatigue=callback;
  activeVideoEl=videoEl;
  
  faceMesh=new FaceMesh({
    locateFile: f=>`https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`
  });
  faceMesh.setOptions({maxNumFaces:1,refineLandmarks:true,
    minDetectionConfidence:0.5,minTrackingConfidence:0.5});
  faceMesh.onResults(onResults);
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 320, height: 240, facingMode: "user" }
    });
    videoEl.srcObject = stream;
    videoEl.play();
    isRunning=true;
    runLoop(videoEl);
    return true;
  } catch (err) {
    console.error("Camera access failed:", err);
    return false;
  }
};

export const stopFatigueMonitoring = () => {
  isRunning=false;
  if (frameTimeoutId) clearTimeout(frameTimeoutId);
  try {
    if (activeVideoEl && activeVideoEl.srcObject) {
      const stream = activeVideoEl.srcObject;
      stream.getTracks().forEach(t => t.stop());
      activeVideoEl.srcObject = null;
    }
  } catch (_) {}
  faceMesh?.close();
  fatigueScore=0; blinkTs.length=0; activeVideoEl=null;
};

export const getCurrentFatigueScore = () => fatigueScore;
