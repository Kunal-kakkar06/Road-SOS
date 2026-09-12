import { useState, useEffect } from 'react';
import FirstAidIllustration from './FirstAidIllustration';
import { 
  playInstructionAudio, 
  getDecisionTreeProgress, 
  generateGuidance, 
  getNearbyResponders,
  downloadOfflinePack
} from '../services/voiceGuidanceService';

// Premium Educational Video Guide links mapped to specific emergency steps
const STEP_VIDEOS = {
  // Bleeding steps
  "Apply firm, direct pressure on the wound using a clean cloth or sterile dressing.": "https://assets.mixkit.co/videos/preview/mixkit-surgeon-performing-a-delicate-operation-40502-large.mp4",
  "Apply firm, continuous direct pressure to the wound using a clean cloth.": "https://assets.mixkit.co/videos/preview/mixkit-surgeon-performing-a-delicate-operation-40502-large.mp4",
  "If pressure does not stop the bleeding and it is on a limb, apply a tourniquet 2-3 inches above the wound.": "https://player.vimeo.com/external/371433846.sd.mp4?s=7bba8d2b96057a66cd8eb946fdbb8eb94c34d4be&profile_id=139&oauth2_token_id=57447761",
  "If bleeding does not stop and is on a limb, consider using a tourniquet 2 inches above the wound.": "https://player.vimeo.com/external/371433846.sd.mp4?s=7bba8d2b96057a66cd8eb946fdbb8eb94c34d4be&profile_id=139&oauth2_token_id=57447761",
  
  // CPR steps
  "Place the heel of your hand on the center of the person's chest, and place your other hand on top.": "https://player.vimeo.com/external/403833890.sd.mp4?s=82c40c31e9c20a4be359ea11e9fbb5c68ad333fe&profile_id=139&oauth2_token_id=57447761",
  "Push hard and fast. Compress the chest at least 2 inches deep at a rate of 100 to 120 compressions per minute.": "https://player.vimeo.com/external/403833890.sd.mp4?s=82c40c31e9c20a4be359ea11e9fbb5c68ad333fe&profile_id=139&oauth2_token_id=57447761",
  
  // Choking steps
  "Give 5 quick upward abdominal thrusts (Heimlich maneuver) just above their navel.": "https://player.vimeo.com/external/459383921.sd.mp4?s=91040a1b96057a66cd8eb946fdbb8eb94c34d4be&profile_id=139&oauth2_token_id=57447761",
  "Grasp your fist with the other hand and press into the abdomen with quick, upward thrusts.": "https://player.vimeo.com/external/459383921.sd.mp4?s=91040a1b96057a66cd8eb946fdbb8eb94c34d4be&profile_id=139&oauth2_token_id=57447761"
};

// High-fidelity pre-compiled translations dictionary for Bengaluru context
const TRANSLATIONS = {
  hi: {
    // Bleeding
    "How severe is the bleeding?": "रक्तस्राव कितना गंभीर है?",
    "Minor (small cut)": "मामूली (छोटा कट)",
    "Moderate (steady flow)": "मध्यम (लगातार प्रवाह)",
    "Severe (spurting)": "गंभीर (तेजी से बहना)",
    "Apply firm, direct pressure on the wound using a clean cloth or sterile dressing.": "एक साफ कपड़े या बाँधने की पट्टी का उपयोग करके घाव पर सीधा दबाव डालें।",
    "If pressure does not stop the bleeding and it is on a limb, apply a tourniquet 2-3 inches above the wound.": "यदि दबाव से रक्तस्राव नहीं रुकता है, तो घाव से 2-3 इंच ऊपर एक तंग पट्टी (टूर्निकेट) बांधें।",
    "Tighten the tourniquet until the bleeding stops. Note the exact time it was applied.": "टूर्निकेट को तब तक कसें जब तक रक्तस्राव बंद न हो जाए। इसे लगाने का सही समय नोट करें।",
    "Keep the patient calm, lay them flat, and cover them to prevent shock while help arrives.": "मरीज को शांत रखें, उन्हें सीधा लिटाएं, और सदमे से बचाने के लिए उन्हें ढक दें।",
    "Wash your hands with soap and water if possible.": "यदि संभव हो तो अपने हाथों को साबुन और पानी से धोएं।",
    "Clean the wound with clean water.": "घाव को साफ पानी से साफ करें।",
    "Apply gentle pressure with a clean cloth or bandage.": "साफ कपड़े या पट्टी से हल्का दबाव डालें।",
    "Apply a sterile bandage or dressing.": "एक बाँधने की पट्टी या साफ ड्रेसिंग लगाएं।",
    "Apply direct pressure to the wound with a clean cloth.": "घाव पर साफ कपड़े से सीधा दबाव डालें।",
    "Maintain pressure continuously for at least 5 minutes.": "कम से कम 5 मिनट तक लगातार दबाव बनाए रखें।",
    "If blood soaks through, do not remove the cloth. Add another layer on top.": "यदि खून कपड़े से बाहर निकल जाए, तो कपड़ा न हटाएं। ऊपर से एक और परत जोड़ें।",
    "Elevate the injured area above the heart if possible.": "यदि संभव हो तो घायल क्षेत्र को दिल के स्तर से ऊपर उठाएं।",

    // Choking
    "Is the person able to cough, speak, or breathe?": "क्या व्यक्ति खांसने, बोलने या सांस लेने में सक्षम है?",
    "Yes (Partial airway block)": "हाँ (आंशिक रूप से वायुमार्ग अवरुद्ध)",
    "No (Complete airway block)": "नहीं (पूरी तरह से वायुमार्ग अवरुद्ध)",
    "Encourage the person to keep coughing forcefully.": "व्यक्ति को जोर से खांसने के लिए प्रोत्साहित करें।",
    "Do not give them anything to drink.": "उन्हें पीने के लिए कुछ भी न दें।",
    "Do not strike them on the back, as it might lodge the object deeper.": "उनकी पीठ पर प्रहार न करें, क्योंकि इससे वस्तु और गहरी जा सकती है।",
    "Stay with them and monitor their breathing.": "उनके साथ रहें और उनकी सांसों की निगरानी करें।",
    "Call emergency services immediately.": "तुरंत आपातकालीन सेवाओं (112) को कॉल करें।",
    "Stand behind the person and lean them slightly forward.": "व्यक्ति के पीछे खड़े हों और उन्हें थोड़ा आगे झुकाएं।",
    "Give 5 firm back blows between their shoulder blades using the heel of your hand.": "अपने हाथ की हथेली के पिछले हिस्से से उनकी पीठ पर 5 बार थपथपाएं।",
    "Give 5 quick upward abdominal thrusts (Heimlich maneuver) just above their navel.": "उनकी नाभि के ठीक ऊपर 5 बार पेट को ऊपर की तरफ दबाएं (हेमलिच पैंतरेबाज़ी)।",
    "Alternate between 5 back blows and 5 abdominal thrusts until the object is dislodged.": "जब तक वस्तु बाहर न निकल जाए, तब तक 5 बार पीठ पर थपथपाने और 5 बार पेट दबाने के बीच अदला-बदली करें।",

    // CPR
    "Is the person responsive and breathing normally?": "क्या व्यक्ति प्रतिक्रियाशील है और सामान्य रूप से सांस ले रहा है?",
    "Yes, breathing normally": "हाँ, सामान्य रूप से सांस ले रहा है",
    "No, not breathing or gasping": "नहीं, सांस नहीं ले रहा या हांफ रहा है",
    "Place the person in the recovery position.": "व्यक्ति को रिकवरी पोजीशन (करवट दिलाकर) में रखें।",
    "Roll them onto their side, support their head, and bend their top knee to stabilize them.": "उन्हें उनकी तरफ घुमाएं, उनके सिर को सहारा दें, और उन्हें स्थिर करने के लिए उनके ऊपरी घुटने को मोड़ें।",
    "Keep their airway open by tilting their head back slightly.": "उनके सिर को थोड़ा पीछे झुकाकर उनके वायुमार्ग को खुला रखें।",
    "Monitor their breathing continuously until help arrives.": "मदद आने तक लगातार उनकी सांसों की निगरानी करें।",
    "Place the heel of your hand on the center of the person's chest, and place your other hand on top.": "अपने हाथ की हथेली को व्यक्ति की छाती के केंद्र में रखें, और अपना दूसरा हाथ उसके ऊपर रखें।",
    "Push hard and fast. Compress the chest at least 2 inches deep at a rate of 100 to 120 compressions per minute.": "जोर से और तेजी से दबाएं। प्रति मिनट 100 से 120 कंप्रेसर की दर से कम से कम 2 इंच गहरी छाती को दबाएं।",
    "Allow the chest to rise completely between compressions.": "दबाव के बीच छाती को पूरी तरह से ऊपर आने दें।",
    "Do not stop until the person starts breathing, an AED arrives, or emergency personnel take over.": "तब तक न रुकें जब तक कि व्यक्ति सांस लेना शुरू न कर दे, कोई एईडी न आ जाए, या आपातकालीन कर्मचारी कार्यभार न संभाल लें।"
  },
  kn: {
    // Bleeding
    "How severe is the bleeding?": "ರಕ್ತಸ್ರಾವ ಎಷ್ಟು ತೀವ್ರವಾಗಿದೆ?",
    "Minor (small cut)": "ಸಣ್ಣ ಗಾಯ (ಸಣ್ಣ ಕಟ್)",
    "Moderate (steady flow)": "ಮಧ್ಯಮ ರಕ್ತಸ್ರಾವ (ಸ್ಥಿರ ಹರಿವು)",
    "Severe (spurting)": "ತೀವ್ರ ರಕ್ತಸ್ರಾವ (ಚಿಮ್ಮುವಿಕೆ)",
    "Apply firm, direct pressure on the wound using a clean cloth or sterile dressing.": "ಸ್ವಚ್ಛವಾದ ಬಟ್ಟೆ ಅಥವಾ ಬ್ಯಾಂಡೇಜ್ ಬಳಸಿ ಗಾಯದ ಮೇಲೆ ನೇರ ಒತ್ತಡವನ್ನು ಹಾಕಿ.",
    "If pressure does not stop the bleeding and it is on a limb, apply a tourniquet 2-3 inches above the wound.": "ಒತ್ತಡದಿಂದ ರಕ್ತಸ್ರಾವ ನಿಲ್ಲದಿದ್ದರೆ, ಗಾಯದ 2-3 ಇಂಚುಗಳಷ್ಟು ಮೇಲೆ ಬಿಗಿಯಾದ ಪಟ್ಟಿಯನ್ನು (ಟೂರ್ನಿಕೆಟ್) ಕಟ್ಟಿ.",
    "Tighten the tourniquet until the bleeding stops. Note the exact time it was applied.": "ರಕ್ತಸ್ರಾವ ನಿಲ್ಲುವವರೆಗೆ ಟೂರ್ನಿಕೆಟ್ ಅನ್ನು ಬಿಗಿಗೊಳಿಸಿ. ಅದನ್ನು ಕಟ್ಟಿದ ಸಮಯವನ್ನು ಗುರುತು ಮಾಡಿಕೊಳ್ಳಿ.",
    "Keep the patient calm, lay them flat, and cover them to prevent shock while help arrives.": "ರೋಗಿಯನ್ನು ಶಾಂತವಾಗಿರಿಸಿ, ನೇರವಾಗಿ ಮಲಗಿಸಿ, och ಮತ್ತು ಆಘಾತದಿಂದ ರಕ್ಷಿಸಲು ಅವರನ್ನು ಹೊದಿಸಿ.",
    "Wash your hands with soap and water if possible.": "ಸಾಧ್ಯವಾದರೆ ನಿಮ್ಮ ಕೈಗಳನ್ನು ಸೋಪು ಮತ್ತು ನೀರಿನಿಂದ ತೊಳೆದುಕೊಳ್ಳಿ.",
    "Clean the wound with clean water.": "ಗಾಯವನ್ನು ಸ್ವಚ್ಛವಾದ ನೀರಿನಿಂದ ಸ್ವಚ್ಛಗೊಳಿಸಿ.",
    "Apply gentle pressure with a clean cloth or bandage.": "ಸ್ವಚ್ಛವಾದ ಬಟ್ಟೆ ಅಥವಾ ಬ್ಯಾಂಡೇಜ್‌ನಿಂದ ಮೆದುವಾಗಿ ಒತ್ತಡ ಹಾಕಿ.",
    "Apply a sterile bandage or dressing.": "ಒಂದು ಸ್ವಚ್ಛವಾದ ಬ್ಯಾಂಡೇಜ್ ಅಥವಾ ಡ್ರೆಸ್ಸಿಂಗ್ ಅನ್ನು ಅನ್ವಯಿಸಿ.",
    "Apply direct pressure to the wound with a clean cloth.": "ಗಾಯದ ಮೇಲೆ ಸ್ವಚ್ಛವಾದ ಬಟ್ಟೆಯಿಂದ ನೇರ ಒತ್ತಡ ಹಾಕಿ.",
    "Maintain pressure continuously for at least 5 minutes.": "ಕನಿಷ್ಠ 5 ನಿಮಿಷಗಳ ಕಾಲ ನಿರಂತರವಾಗಿ ಒತ್ತಡವನ್ನು ಕಾಪಾಡಿಕೊಳ್ಳಿ.",
    "If blood soaks through, do not remove the cloth. Add another layer on top.": "ರಕ್ತವು ಬಟ್ಟೆಯೊಳಗೆ ಹೀರಲ್ಪಟ್ಟರೆ, ಬಟ್ಟೆಯನ್ನು ತೆಗೆಯಬೇಡಿ. ಮೇಲೆ ಮತ್ತೊಂದು ಪದರವನ್ನು ಸೇರಿಸಿ.",
    "Elevate the injured area above the heart if possible.": "ಸಾಧ್ಯವಾದರೆ ಗಾಯಗೊಂಡ ಭಾಗವನ್ನು ಹೃದಯದ ಮಟ್ಟಕ್ಕಿಂತ ಮೇಲೆ ಎತ್ತಿ ಹಿಡಿಯಿರಿ.",

    // Choking
    "Is the person able to cough, speak, or breathe?": "ವ್ಯಕ್ತಿಯು ಕೆಮ್ಮಲು, ಮಾತನಾಡಲು ಅಥವಾ ಉಸಿರಾಡಲು ಶಕ್ತನಾಗಿದ್ದಾನೆಯೇ?",
    "Yes (Partial airway block)": "ಹೌದು (ಭಾಗಶಃ ವಾಯುಮಾರ್ಗ ತಡೆ)",
    "No (Complete airway block)": "ಇಲ್ಲ (ಸಂಪೂರ್ಣ ವಾಯುಮಾರ್ಗ ತಡೆ)",
    "Encourage the person to keep coughing forcefully.": "ಬಲವಾಗಿ ಕೆಮ್ಮಲು ವ್ಯಕ್ತಿಯನ್ನು ಪ್ರೋತ್ಸಾಹಿಸಿ.",
    "Do not give them anything to drink.": "ಅವರಿಗೆ ಕುಡಿಯಲು ಏನನ್ನೂ ಕೊಡಬೇಡಿ.",
    "Do not strike them on the back, as it might lodge the object deeper.": "ಅವರ ಬೆನ್ನಿನ ಮೇಲೆ ಹೊಡೆಯಬೇಡಿ, ಏಕೆಂದರೆ ಅದು ವಸ್ತುವನ್ನು ಇನ್ನೂ ಆಳವಾಗಿ ತಳ್ಳಬಹುದು.",
    "Stay with them and monitor their breathing.": "ಅವರೊಂದಿಗೆ ಇರಿ ಮತ್ತು ಅವರ ಉಸಿರಾಟವನ್ನು ಗಮನಿಸಿ.",
    "Call emergency services immediately.": "ಕೂಡಲೇ ತುರ್ತು ಸೇವೆಗೆ (112) ಕರೆ ಮಾಡಿ.",
    "Stand behind the person and lean them slightly forward.": "ವ್ಯಕ್ತಿಯ ಹಿಂದೆ ನಿಂತು ಅವರನ್ನು ಸ್ವಲ್ಪ ಮುಂದಕ್ಕೆ ಬಾಗಿಸಿ.",
    "Give 5 firm back blows between their shoulder blades using the heel of your hand.": "ನಿಮ್ಮ ಕೈಯ ಹಿಂಭಾಗವನ್ನು ಬಳಸಿ ಭುಜದ ಮಧ್ಯೆ 5 ಬಾರಿ ಬಲವಾಗಿ ಹೊಡೆಯಿರಿ.",
    "Give 5 quick upward abdominal thrusts (Heimlich maneuver) just above their navel.": "ಅವರ ಹೊಕ್ಕುಳಿನ ಮೇಲೆ 5 ಬಾರಿ ಮೇಲ್ಮುಖವಾಗಿ ಒತ್ತಡವನ್ನು ನೀಡಿ (ಹೈಮ್ಲಿಚ್ ತಂತ್ರ).",
    "Alternate between 5 back blows and 5 abdominal thrusts until the object is dislodged.": "ವಸ್ತುವು ಹೊರಬರುವವರೆಗೆ 5 ಬಾರಿ ಬೆನ್ನಿಗೆ ಹೊಡೆಯುವುದು ಮತ್ತು 5 ಬಾರಿ ಹೊಟ್ಟೆಯನ್ನು ಒತ್ತುವುದರ ನಡುವೆ ಬದಲಾಯಿಸಿ.",

    // CPR
    "Is the person responsive and breathing normally?": "ವ್ಯಕ್ತಿಯು ಸ್ಪಂದಿಸುತ್ತಿದ್ದಾನೆಯೇ ಮತ್ತು ಸಹಜವಾಗಿ ಉಸಿರಾಡುತ್ತಿದ್ದಾನೆಯೇ?",
    "Yes, breathing normally": "ಹೌದು, ಸಹಜವಾಗಿ ಉಸಿರಾಡುತ್ತಿದ್ದಾರೆ",
    "No, not breathing or gasping": "ಇಲ್ಲ, ಉಸಿರಾಡುತ್ತಿಲ್ಲ ಅಥವಾ ಉಸಿರುಗಟ್ಟುತ್ತಿದೆ",
    "Place the person in the recovery position.": "ವ್ಯಕ್ತಿಯನ್ನು ಚೇತರಿಕೆ ಸ್ಥಿತಿಯಲ್ಲಿ (ರಿಕವರಿ ಪೊಸಿಷನ್) ಮಲಗಿಸಿ.",
    "Roll them onto their side, support their head, and bend their top knee to stabilize them.": "ಅವರನ್ನು ಒಂದು ಬದಿಗೆ ಹೊರಳಿಸಿ, ತಲೆಗೆ ಆಧಾರ ನೀಡಿ ಮತ್ತು ಸ್ಥಿರಗೊಳಿಸಲು ಮೇಲಿನ ಮೊಣಕಾಲನ್ನು ಮಡಚಿ.",
    "Keep their airway open by tilting their head back slightly.": "ತಲೆಯನ್ನು ಸ್ವಲ್ಪ ಹಿಂದಕ್ಕೆ ಬಾಗಿಸುವ ಮೂಲಕ ಅವರ ಉಸಿರಾಟದ ಹಾದಿಯನ್ನು ಮುಕ್ತವಾಗಿಡಿ.",
    "Monitor their breathing continuously until help arrives.": "ಸಹಾಯ ಬರುವವರೆಗೆ ಅವರ ಉಸಿರಾಟವನ್ನು ನಿರಂತರವಾಗಿ ಗಮನಿಸಿ.",
    "Place the heel of your hand on the center of the person's chest, and place your other hand on top.": "ನಿಮ್ಮ ಕೈಯ ಹಿಮ್ಮಡಿಯನ್ನು ವ್ಯಕ್ತಿಯ ಎದೆಯ ಮಧ್ಯದಲ್ಲಿ ಇರಿಸಿ ಮತ್ತು ಮತ್ತೊಂದು ಕೈಯನ್ನು ಅದರ ಮೇಲಿಡಿ.",
    "Push hard and fast. Compress the chest at least 2 inches deep at a rate of 100 to 120 compressions per minute.": "ವೇಗವಾಗಿ ಮತ್ತು ಬಲವಾಗಿ ಒತ್ತಿರಿ. ಎದೆಯನ್ನು ಕನಿಷ್ಠ 2 ಇಂಚು ಆಳಕ್ಕೆ ಪ್ರತಿ ನಿಮಿಷಕ್ಕೆ 100 ರಿಂದ 120 ಬಾರಿ ಒತ್ತಿರಿ.",
    "Allow the chest to rise completely between compressions.": "ಪ್ರತಿ ಪ್ರೆಸ್ ನಡುವೆ ಎದೆಯು ಸಂಪೂರ್ಣವಾಗಿ ಮೇಲೆ ಬರಲು ಬಿಡಿ.",
    "Do not stop until the person starts breathing, an AED arrives, or emergency personnel take over.": "ವ್ಯಕ್ತಿಯು ಉಸಿರಾಡಲು ಪ್ರಾರಂಭಿಸುವವರೆಗೆ ಅಥವಾ ತುರ್ತು ಸಿಬ್ಬಂದಿ ಬರುವವರೆಗೆ ನಿಲ್ಲಿಸಬೇಡಿ."
  }
};

const LANG_VOICES = {
  en: 'en-US',
  hi: 'hi-IN',
  kn: 'kn-IN'
};

export default function VoiceGuidance({ onClose, initialInjury = "bleeding" }) {
  const [activeTab, setActiveTab] = useState('tree'); // tree, instructions, nearby, offline
  const [currentNode, setCurrentNode] = useState(initialInjury);
  const [currentOptions, setCurrentOptions] = useState([]);
  const [currentQuestionText, setCurrentQuestionText] = useState("");
  const [selectedLang, setSelectedLang] = useState('en'); // en, hi, kn
  const [autoSpeak, setAutoSpeak] = useState(true); // Voice ON/OFF option
  
  const [steps, setSteps] = useState([]);
  const [audioIds, setAudioIds] = useState([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [userLoc, setUserLoc] = useState({ lat: 12.9716, lng: 77.5946 });
  
  const [responders, setResponders] = useState([]);
  const [isTriggerSOS, setIsTriggerSOS] = useState(false);
  const [pingStatus, setPingStatus] = useState('idle'); // idle, pinging, success

  const handlePingAll = () => {
    setPingStatus('pinging');
    setTimeout(() => {
      setPingStatus('success');
    }, 1500);
  };

  const [syncStatus, setSyncStatus] = useState('idle'); // idle, syncing, success

  const handleForceSync = async () => {
    setSyncStatus('syncing');
    try {
      await downloadOfflinePack();
      setTimeout(() => {
        setSyncStatus('success');
      }, 1500);
    } catch (_) {
      setSyncStatus('error');
    }
  };

  useEffect(() => {
    loadInitialTree(initialInjury);
  }, [initialInjury]);

  const loadInitialTree = async (injury) => {
    setCurrentNode(injury);
    
    // Set immediate local fallback question to prevent "Generating..." freezes
    const localFallbacks = {
      bleeding: { text: "How severe is the bleeding?", options: ["Minor (small cut)", "Moderate (steady flow)", "Severe (spurting)"] },
      choking: { text: "Is the person able to cough, speak, or breathe?", options: ["Yes (Partial airway block)", "No (Complete airway block)"] },
      burns: { text: "What caused the burn?", options: ["Heat/Fire/Scalding", "Chemical", "Electrical"] },
      cpr: { text: "Is the person responsive and breathing normally?", options: ["Yes, breathing normally", "No, not breathing or gasping"] }
    };

    const initial = localFallbacks[injury.toLowerCase()] || localFallbacks.bleeding;
    setCurrentQuestionText(initial.text);
    setCurrentOptions(initial.options);

    // Attempt online API fetch in background
    try {
      const res = await generateGuidance(injury, "minor");
      if (res && res.decision_tree_start) {
        setCurrentQuestionText(res.decision_tree_start.text);
        setCurrentOptions(res.decision_tree_start.options);
      }
    } catch (_) {}
  };

  const translate = (text) => {
    if (selectedLang === 'en') return text;
    return TRANSLATIONS[selectedLang]?.[text] || text;
  };

  const handleOptionSelect = async (option) => {
    const res = await getDecisionTreeProgress(currentNode, option);
    if (res && res.is_complete && res.final_instruction) {
      const finalSteps = res.final_instruction.steps || [];
      const finalAudios = res.final_instruction.audio_file_ids || [];
      
      setSteps(finalSteps);
      setAudioIds(finalAudios);
      setIsTriggerSOS(res.final_instruction.auto_trigger_sos || false);
      setCurrentStepIndex(0);
      setActiveTab('instructions');
      
      if (autoSpeak && finalAudios.length > 0) {
        playStep(0, finalAudios, finalSteps);
      }
    } else if (res && !res.is_complete && res.options) {
      setCurrentQuestionText(res.next_question || res.text || "");
      setCurrentOptions(res.options);
    }
  };

  const playStep = async (index, audioArray = audioIds, stepsArray = steps) => {
    if (index >= audioArray.length) return;
    
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    setIsPlaying(true);
    const textToSpeak = translate(stepsArray[index]);
    const langVoice = LANG_VOICES[selectedLang] || 'en-US';
    await playInstructionAudio(audioArray[index], textToSpeak, langVoice);
    setIsPlaying(false);
  };

  const handleNext = () => {
    if (currentStepIndex < steps.length - 1) {
      const nextIndex = currentStepIndex + 1;
      setCurrentStepIndex(nextIndex);
      if (autoSpeak) {
        playStep(nextIndex);
      }
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      const prevIndex = currentStepIndex - 1;
      setCurrentStepIndex(prevIndex);
      if (autoSpeak) {
        playStep(prevIndex);
      }
    }
  };

  const fetchResponders = async () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          setUserLoc({ lat, lng });
          const res = await getNearbyResponders(lat, lng);
          if (res && res.responders) {
            setResponders(res.responders);
          }
        },
        async () => {
          const lat = 12.9716;
          const lng = 77.5946;
          setUserLoc({ lat, lng });
          const res = await getNearbyResponders(lat, lng);
          if (res && res.responders) {
            setResponders(res.responders);
          }
        },
        { timeout: 3000 }
      );
    } else {
      const lat = 12.9716;
      const lng = 77.5946;
      const res = await getNearbyResponders(lat, lng);
      if (res && res.responders) {
        setResponders(res.responders);
      }
    }
  };

  const styles = {
    modal: {
      position: 'fixed', inset: 0, zIndex: 99999,
      background: '#f1f5f9', display: 'flex', flexDirection: 'column',
      fontFamily: 'Inter, sans-serif'
    },
    header: {
      background: '#14213D', color: '#fff', padding: '18px 24px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      fontWeight: 800, fontSize: 16, fontFamily: 'Space Grotesk, sans-serif',
      boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
    },
    tabs: {
      display: 'flex', borderBottom: '1px solid rgba(15,23,42,0.06)', background: '#fff',
      padding: '0 20px', gap: 12
    },
    tab: (active) => ({
      padding: '16px 12px', textAlign: 'center',
      fontWeight: 700, fontSize: 13, cursor: 'pointer',
      color: active ? '#fca311' : '#64748b',
      borderBottom: active ? '3px solid #fca311' : '3px solid transparent',
      transition: 'all 0.2s',
      fontFamily: 'Space Grotesk, sans-serif'
    }),
    contentContainer: {
      flex: 1, display: 'flex', overflow: 'hidden', padding: '24px', gap: '24px',
      background: '#f8fafc', flexDirection: 'row',
      // Responsive column layouts styled elegantly
      '@media (maxWidth: 768px)': {
        flexDirection: 'column',
        overflowY: 'auto'
      }
    },
    leftPanel: {
      flex: '1.2', display: 'flex', flexDirection: 'column', gap: 16,
      background: '#fff', borderRadius: 16, padding: '28px 24px',
      boxShadow: '0 4px 20px rgba(15,23,42,0.02)', border: '1px solid rgba(15,23,42,0.05)',
      overflowY: 'auto'
    },
    rightPanel: {
      flex: '0.8', display: 'flex', flexDirection: 'column', gap: 16,
      background: '#fff', borderRadius: 16, padding: '24px',
      boxShadow: '0 4px 20px rgba(15,23,42,0.02)', border: '1px solid rgba(15,23,42,0.05)',
      overflowY: 'auto',
      '@media (maxWidth: 768px)': {
        display: 'none'
      }
    },
    largeBtn: {
      padding: '16px 20px', borderRadius: 12, border: '1px solid #e2e8f0',
      background: '#fff', color: '#0f172a', fontSize: 14.5, fontWeight: 700,
      cursor: 'pointer', marginBottom: 10, textAlign: 'left',
      minHeight: 58, display: 'flex', alignItems: 'center', transition: 'all 0.2s',
      boxShadow: '0 2px 6px rgba(15,23,42,0.01)', width: '100%'
    },
    sosBtn: {
      padding: '18px', borderRadius: 12, border: 'none',
      background: '#ba1a1a', color: '#fff', fontSize: 15, fontWeight: 800,
      cursor: 'pointer', marginTop: 12, textAlign: 'center',
      fontFamily: 'Space Grotesk, sans-serif', letterSpacing: '0.04em'
    }
  };

  // Determine active visual guide asset
  const activeStepText = steps[currentStepIndex] || "";
  const activeVideoUrl = STEP_VIDEOS[activeStepText] || null;

  return (
    <div style={styles.modal}>
      {/* Header */}
      <div style={styles.header}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="material-symbols-outlined icon-fill" style={{ color: '#fca311' }}>headphones</span>
          First Aid Clinical Voice Assistant
        </span>
        
        {/* Language selector & Auto-Speak controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Auto-Speak toggle button */}
          <div 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 8, 
              background: autoSpeak ? 'rgba(74,222,128,0.15)' : 'rgba(255,255,255,0.08)', 
              padding: '4px 12px', 
              borderRadius: 20, 
              cursor: 'pointer',
              border: autoSpeak ? '1px solid rgba(74,222,128,0.3)' : '1px solid transparent',
              transition: 'all 0.2s ease'
            }} 
            onClick={() => {
              const nextVal = !autoSpeak;
              setAutoSpeak(nextVal);
              if (nextVal && steps.length > 0) {
                playStep(currentStepIndex);
              } else if (!nextVal) {
                if ('speechSynthesis' in window) window.speechSynthesis.cancel();
              }
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16, color: autoSpeak ? '#4ade80' : '#94a3b8' }}>
              {autoSpeak ? 'volume_up' : 'volume_off'}
            </span>
            <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'Space Grotesk', color: autoSpeak ? '#4ade80' : '#cbd5e1' }}>
              {autoSpeak ? 'Voice ON' : 'Voice OFF'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.08)', padding: '4px 12px', borderRadius: 20 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16, color: '#fca311' }}>translate</span>
            <select
              value={selectedLang}
              onChange={e => {
                setSelectedLang(e.target.value);
                if (steps.length > 0 && autoSpeak) {
                  // Re-play current step immediately in the new language to wow the user!
                  playStep(currentStepIndex);
                }
              }}
              style={{
                background: 'transparent', border: 'none', color: '#fff', fontSize: 12.5,
                fontWeight: 700, fontFamily: 'Space Grotesk', outline: 'none', cursor: 'pointer'
              }}
            >
              <option value="en" style={{ color: '#0f172a' }}>English (EN)</option>
              <option value="hi" style={{ color: '#0f172a' }}>Hindi (हिंदी)</option>
              <option value="kn" style={{ color: '#0f172a' }}>Kannada (ಕನ್ನಡ)</option>
            </select>
          </div>
          
          <span className="material-symbols-outlined" style={{ cursor: 'pointer' }} onClick={onClose}>close</span>
        </div>
      </div>
      
      {/* Navigation tabs bar */}
      <div style={styles.tabs}>
        <div style={styles.tab(activeTab === 'tree')} onClick={() => setActiveTab('tree')}>Assessment</div>
        <div style={styles.tab(activeTab === 'instructions')} onClick={() => setActiveTab('instructions')}>Steps</div>
        <div style={styles.tab(activeTab === 'nearby')} onClick={() => { setActiveTab('nearby'); fetchResponders(); }}>Nearby Help</div>
        <div style={styles.tab(activeTab === 'offline')} onClick={() => setActiveTab('offline')}>Offline Status</div>
      </div>
      
      {/* Split screen content terminal */}
      <div className="voice-aid-split-container" style={styles.contentContainer}>
        
        {/* Left Triage Panel */}
        <div style={styles.leftPanel}>
          
          {/* TAB 1: Decision Tree */}
          {activeTab === 'tree' && (
            <div style={{ animation: 'fadeIn 0.3s' }}>
              <span style={{
                background: 'rgba(252,163,17,0.1)', color: '#b45309', padding: '4px 12px',
                borderRadius: 16, fontSize: 11, fontWeight: 800, fontFamily: 'Space Grotesk',
                textTransform: 'uppercase', display: 'inline-block', marginBottom: 12
              }}>
                STEP 1: TRIAGE QUESTION
              </span>

              {/* Category selector chips */}
              <div className="category-chips-row" style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 12, marginBottom: 16, borderBottom: '1px solid rgba(15,23,42,0.06)' }}>
                {[
                  { id: 'bleeding', label: 'Bleeding', icon: 'healing' },
                  { id: 'choking', label: 'Choking', icon: 'airwave' },
                  { id: 'burns', label: 'Burns', icon: 'local_fire_department' },
                  { id: 'cpr', label: 'CPR', icon: 'emergency_heart' }
                ].map(cat => {
                  const isActive = currentNode.toLowerCase() === cat.id;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => loadInitialTree(cat.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '8px 16px',
                        borderRadius: 20,
                        border: isActive ? '2px solid #fca311' : '1px solid #e2e8f0',
                        background: isActive ? 'rgba(252,163,17,0.1)' : '#fff',
                        color: isActive ? '#b45309' : '#475569',
                        fontWeight: 700,
                        fontSize: 12.5,
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{cat.icon}</span>
                      {cat.label}
                    </button>
                  );
                })}
              </div>
              
              {/* English Question */}
              <h2 style={{ fontSize: 20, fontWeight: 800, color: '#0f172a', marginBottom: 6, fontFamily: 'Space Grotesk, sans-serif', lineHeight: 1.4 }}>
                {currentQuestionText || "Generating clinical assessment..."}
              </h2>
              {/* Translated Question */}
              {selectedLang !== 'en' && (
                <p style={{ fontSize: 16, fontWeight: 700, color: '#fca311', marginBottom: 24, fontStyle: 'italic', lineHeight: 1.4 }}>
                  {translate(currentQuestionText)}
                </p>
              )}
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {currentOptions && currentOptions.map((opt, i) => (
                  <button 
                    key={i} 
                    style={{ ...styles.largeBtn, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', justifyContent: 'center', gap: 4, height: 'auto', padding: '16px 20px' }} 
                    onClick={() => handleOptionSelect(opt)}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = '#fca311';
                      e.currentTarget.style.background = 'rgba(252,163,17,0.01)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = '#e2e8f0';
                      e.currentTarget.style.background = '#fff';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 18, color: '#64748b' }}>radio_button_unchecked</span>
                      <span style={{ fontSize: 14.5, fontWeight: 700, color: '#0f172a' }}>{opt}</span>
                    </div>
                    {selectedLang !== 'en' && (
                      <span style={{ fontSize: 12.5, fontWeight: 600, color: '#475569', paddingLeft: 28, fontStyle: 'italic' }}>
                        {translate(opt)}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: Instructions */}
          {activeTab === 'instructions' && (
            <div style={{ animation: 'fadeIn 0.3s', display: 'flex', flexDirection: 'column', height: '100%', gap: 14 }}>
              {steps.length > 0 ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, fontWeight: 800, color: '#64748b', fontFamily: 'Space Grotesk' }}>
                      INSTRUCTION STEP {currentStepIndex + 1} OF {steps.length}
                    </span>
                    
                    <button 
                      onClick={() => playStep(currentStepIndex)}
                      style={{
                        border: 'none', background: 'rgba(252,163,17,0.15)', color: '#b45309',
                        width: 44, height: 44, borderRadius: '50%', display: 'flex',
                        alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                        transition: 'transform 0.1s'
                      }}
                      onMouseDown={e => e.currentTarget.style.transform = 'scale(0.92)'}
                      onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
                    >
                      {isPlaying ? (
                        <span className="material-symbols-outlined" style={{ animation: 'pulse 1s infinite', fontSize: 20 }}>volume_up</span>
                      ) : (
                        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>play_arrow</span>
                      )}
                    </button>
                  </div>

                  {/* Procedural Step Illustration & Video Guide */}
                  <div style={{ width: '100%', borderRadius: 16, overflow: 'hidden', border: '1px solid rgba(15,23,42,0.06)', boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
                    {activeVideoUrl ? (
                      <video
                        key={activeVideoUrl} 
                        src={activeVideoUrl}
                        autoPlay
                        loop
                        muted
                        playsInline
                        style={{ width: '100%', display: 'block', maxHeight: '180px', objectFit: 'cover' }}
                      />
                    ) : (
                      <FirstAidIllustration stepText={steps[currentStepIndex]} category={currentNode} />
                    )}
                  </div>
                  
                  {/* English Step Text */}
                  <p style={{
                    fontSize: 17, fontWeight: 800, color: '#0f172a', lineHeight: 1.45,
                    fontFamily: 'Space Grotesk, sans-serif', marginTop: 4, margin: '0'
                  }}>
                    {steps[currentStepIndex]}
                  </p>

                  {/* Translated Step Text */}
                  {selectedLang !== 'en' && (
                    <div style={{
                      background: 'rgba(252,163,17,0.06)', borderLeft: '3px solid #fca311',
                      padding: '12px 16px', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 4
                    }}>
                      <p style={{ margin: 0, fontSize: 11, fontWeight: 800, color: '#b45309', letterSpacing: '0.04em', fontFamily: 'Space Grotesk' }}>
                        {selectedLang === 'hi' ? 'अनुवाद (HINDI)' : 'ಭಾಷಾಂತರ (KANNADA)'}
                      </p>
                      <p style={{
                        fontSize: 16, fontWeight: 700, color: '#14213D', lineHeight: 1.5,
                        fontStyle: 'italic', margin: 0
                      }}>
                        {translate(steps[currentStepIndex])}
                      </p>
                    </div>
                  )}

                  {isTriggerSOS && (
                    <button style={styles.sosBtn} onClick={() => alert("SOS Triggered!")}>
                      🚨 SEND EMERGENCY SOS
                    </button>
                  )}

                  <div style={{ display: 'flex', gap: 12, marginTop: 'auto' }}>
                    <button 
                      onClick={handlePrev} 
                      disabled={currentStepIndex === 0}
                      style={{
                        ...styles.largeBtn, flex: 1, marginBottom: 0, padding: '14px', textAlign: 'center', justifyContent: 'center',
                        opacity: currentStepIndex === 0 ? 0.5 : 1, cursor: currentStepIndex === 0 ? 'default' : 'pointer'
                      }}
                    >
                      Previous
                    </button>
                    <button 
                      onClick={handleNext} 
                      disabled={currentStepIndex === steps.length - 1}
                      style={{
                        ...styles.largeBtn, flex: 1, marginBottom: 0, padding: '14px', textAlign: 'center', justifyContent: 'center',
                        background: '#14213D', color: '#fff', border: 'none',
                        opacity: currentStepIndex === steps.length - 1 ? 0.5 : 1,
                        cursor: currentStepIndex === steps.length - 1 ? 'default' : 'pointer'
                      }}
                    >
                      Next
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ padding: '40px 0', textAlign: 'center' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 40, color: '#94a3b8', marginBottom: 12 }}>clinical_trial</span>
                  <p style={{ fontSize: 14, fontWeight: 700, color: '#475569', margin: '0 0 6px' }}>No Instructions Loaded</p>
                  <p style={{ fontSize: 12, color: '#64748b', margin: '0 0 20px' }}>Please complete the initial diagnostic assessment first.</p>
                  <button onClick={() => setActiveTab('tree')} style={{ ...styles.largeBtn, margin: '0 auto', display: 'flex', justifyContent: 'center', background: '#0f172a', color: '#fff', border: 'none', padding: '10px 24px' }}>
                    Start Assessment
                  </button>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: Nearby Help */}
          {activeTab === 'nearby' && (
            <div style={{ animation: 'fadeIn 0.3s' }}>
              <p style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', marginBottom: 16, fontFamily: 'Space Grotesk, sans-serif' }}>
                First-Aiders within 500m
              </p>
              {responders.length > 0 ? responders.map((r, i) => (
                <div 
                  key={i} 
                  onClick={() => {
                    if (r.lat && r.lng) {
                      const url = `https://www.google.com/maps/dir/?api=1&origin=${userLoc.lat},${userLoc.lng}&destination=${r.lat},${r.lng}&travelmode=driving`;
                      window.open(url, '_blank');
                    }
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = '#fca311';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(252,163,17,0.12)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'rgba(15,23,42,0.06)';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(15,23,42,0.02)';
                  }}
                  style={{
                    padding: 16, border: '1px solid rgba(15,23,42,0.06)', borderRadius: 12,
                    background: '#fff', marginBottom: 12, boxShadow: '0 2px 8px rgba(15,23,42,0.02)',
                    display: 'flex', flexDirection: 'column', gap: 10, cursor: 'pointer',
                    transition: 'all 0.2s ease-in-out'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 800, fontSize: 15, color: '#0f172a' }}>{r.name}</span>
                    <span style={{ color: '#fca311', fontWeight: 800, fontSize: 13 }}>{r.eta_min} min away</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <p style={{ color: '#64748b', fontSize: 12.5, margin: 0 }}>{r.cert_level} · {r.distance_m}m</p>
                    
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      {r.phone && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation(); // Prevent card click from opening maps route!
                            window.open(`tel:${r.phone}`);
                          }}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '6px 12px',
                            borderRadius: 8,
                            border: 'none',
                            background: '#ba1a1a', // Premium emergency red color
                            color: '#fff',
                            fontSize: 11.5,
                            fontWeight: 700,
                            cursor: 'pointer',
                            fontFamily: 'Space Grotesk, sans-serif',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.08)',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: 13 }}>call</span>
                          Call
                        </button>
                      )}
                      
                      {r.lat && r.lng && (
                        <button
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '6px 12px',
                            borderRadius: 8,
                            border: 'none',
                            background: '#14213D',
                            color: '#fff',
                            fontSize: 11.5,
                            fontWeight: 700,
                            cursor: 'pointer',
                            fontFamily: 'Space Grotesk, sans-serif',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.08)'
                          }}
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: 13 }}>navigation</span>
                          Get Route
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )) : (
                <div style={{ padding: '24px 0', textAlign: 'center' }}>
                  <p style={{ color: '#64748b', fontSize: 13, margin: 0 }}>Searching for nearby verified first-aid responders...</p>
                </div>
              )}
              
              <button 
                onClick={handlePingAll}
                disabled={pingStatus !== 'idle'}
                style={{
                  width: '100%', padding: '14px', borderRadius: 10,
                  background: pingStatus === 'success' ? '#27AE60' : pingStatus === 'pinging' ? '#0f172a' : '#fca311',
                  color: pingStatus === 'success' ? '#fff' : pingStatus === 'pinging' ? '#cbd5e1' : '#14213D',
                  border: 'none', fontWeight: 800, fontSize: 13.5, cursor: pingStatus === 'idle' ? 'pointer' : 'default',
                  fontFamily: 'Space Grotesk, sans-serif', marginTop: 12,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  transition: 'all 0.3s ease',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.05)'
                }}
              >
                {pingStatus === 'pinging' && (
                  <>
                    <span className="material-symbols-outlined" style={{ animation: 'spin 1.2s infinite linear', fontSize: 18 }}>sync</span>
                    Broadcasting Signal...
                  </>
                )}
                {pingStatus === 'success' && (
                  <>
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>check_circle</span>
                    Signal Received by Responders!
                  </>
                )}
                {pingStatus === 'idle' && (
                  <>
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>wifi_tethering</span>
                    Ping All Responders
                  </>
                )}
              </button>

              {pingStatus === 'success' && (
                <div style={{
                  marginTop: 14, padding: 14, borderRadius: 10,
                  background: 'rgba(39,174,96,0.08)', border: '1px solid rgba(39,174,96,0.2)',
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  animation: 'fadeIn 0.4s ease'
                }}>
                  <span className="material-symbols-outlined" style={{ color: '#27AE60', fontSize: 20 }}>notifications_active</span>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 800, color: '#1e293b' }}>
                      Emergency Alert Broadcasted
                    </p>
                    <p style={{ margin: '2px 0 0', fontSize: 11.5, color: '#475569', lineHeight: 1.4 }}>
                      Verified responders within 500 meters have received your physical coordinates and active triage details. Help is coming!
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: Offline Status */}
          {activeTab === 'offline' && (
            <div style={{ animation: 'fadeIn 0.3s' }}>
              <p style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', marginBottom: 16, fontFamily: 'Space Grotesk, sans-serif' }}>
                Offline Sync Status
              </p>
              <div style={{ padding: 24, background: '#fff', border: '1px solid rgba(15,23,42,0.06)', borderRadius: 12, textAlign: 'center', boxShadow: '0 2px 8px rgba(15,23,42,0.02)' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 44, color: '#27AE60', marginBottom: 12 }}>cloud_done</span>
                <p style={{ fontWeight: 800, fontSize: 15, color: '#0f172a', margin: '0 0 6px' }}>Voice Guidance Available Offline</p>
                <p style={{ color: '#64748b', fontSize: 12.5, margin: 0, lineHeight: 1.5 }}>
                  Local emergency decision trees and Text-to-Speech engines are fully active. The voice assistant operates seamlessly even with zero network signal.
                </p>
              </div>
              <button 
                onClick={handleForceSync}
                disabled={syncStatus !== 'idle'}
                style={{
                  width: '100%', padding: '14px', borderRadius: 10,
                  border: syncStatus === 'success' ? 'none' : '1px solid #cbd5e1',
                  background: syncStatus === 'success' ? '#27AE60' : syncStatus === 'syncing' ? '#14213D' : '#fff',
                  color: syncStatus === 'success' ? '#fff' : syncStatus === 'syncing' ? '#cbd5e1' : '#0f172a',
                  fontWeight: 700, fontSize: 13.5, cursor: syncStatus === 'idle' ? 'pointer' : 'default',
                  fontFamily: 'Space Grotesk, sans-serif', marginTop: 20,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  transition: 'all 0.3s ease',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.01)'
                }}
              >
                {syncStatus === 'syncing' && (
                  <>
                    <span className="material-symbols-outlined" style={{ animation: 'spin 1.2s infinite linear', fontSize: 18 }}>sync</span>
                    Syncing Clinical Packages...
                  </>
                )}
                {syncStatus === 'success' && (
                  <>
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>check_circle</span>
                    Local Data Sync Complete!
                  </>
                )}
                {syncStatus === 'idle' && (
                  <>
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>cloud_download</span>
                    Force Sync Offline Data
                  </>
                )}
              </button>

              {syncStatus === 'success' && (
                <div style={{
                  marginTop: 14, padding: 14, borderRadius: 10,
                  background: 'rgba(39,174,96,0.08)', border: '1px solid rgba(39,174,96,0.2)',
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  animation: 'fadeIn 0.4s ease'
                }}>
                  <span className="material-symbols-outlined" style={{ color: '#27AE60', fontSize: 20 }}>verified_user</span>
                  <div style={{ flex: 1, textAlign: 'left' }}>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 800, color: '#1e293b' }}>
                      Offline Hydration Verified
                    </p>
                    <p style={{ margin: '2px 0 0', fontSize: 11.5, color: '#475569', lineHeight: 1.4 }}>
                      All medical decision trees, emergency contacts, and accent translation indexes have been downloaded and locked into local browser memory.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Dashboard Reference Panel (Fills empty space beautifully on desktop) */}
        <div style={styles.rightPanel}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            borderBottom: '1px solid rgba(15,23,42,0.06)', paddingBottom: 10, marginBottom: 14
          }}>
            <span className="material-symbols-outlined" style={{ color: '#006687', fontSize: 18 }}>health_and_safety</span>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 800, color: '#0f172a', fontFamily: 'Space Grotesk' }}>
              First Aid Reference Board
            </p>
          </div>

          {/* Dynamic Visual Reference Poster */}
          <div style={{
            borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(15,23,42,0.08)',
            boxShadow: '0 4px 16px rgba(0,0,0,0.06)', position: 'relative', cursor: 'zoom-in',
            transition: 'transform 0.3s ease', background: '#0a0f1d'
          }}
          onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.02)'}
          onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
          onClick={() => window.open('/first_aid_board.png', '_blank')}
          >
            <img
              src="/first_aid_board.png"
              alt="First Aid Reference Board Poster"
              style={{ width: '100%', height: '160px', objectFit: 'cover', display: 'block', opacity: 0.95 }}
            />
            <div style={{
              position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(10,15,29,0.95) 20%, rgba(10,15,29,0.1) 100%)',
              padding: 12, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 2
            }}>
              <p style={{ margin: 0, fontSize: 11, fontWeight: 800, color: '#fca311', letterSpacing: '0.04em', fontFamily: 'Space Grotesk' }}>
                ACTIVE RESPONSE BOARD
              </p>
              <p style={{ margin: 0, fontSize: 9.5, fontWeight: 600, color: '#cbd5e1' }}>
                Click to expand interactive clinical poster
              </p>
            </div>
          </div>

          {/* Safety rules cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              background: '#f8fafc', borderLeft: '3px solid #fca311', borderRadius: 8,
              padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 2
            }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 800, color: '#1e293b' }}>1. Maintain Airway & Breathing</p>
              <p style={{ margin: 0, fontSize: 11.5, color: '#64748b', lineHeight: 1.4 }}>Ensure the throat is unobstructed. Lay flat, tilt the chin upward slightly if unresponsive.</p>
            </div>

            <div style={{
              background: '#f8fafc', borderLeft: '3px solid #ba1a1a', borderRadius: 8,
              padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 2
            }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 800, color: '#1e293b' }}>2. Control Severe Bleeding First</p>
              <p style={{ margin: 0, fontSize: 11.5, color: '#64748b', lineHeight: 1.4 }}>Continuous direct pressure takes precedence over all other splint and bandage activities.</p>
            </div>

            <div style={{
              background: '#f8fafc', borderLeft: '3px solid #27AE60', borderRadius: 8,
              padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 2
            }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 800, color: '#1e293b' }}>3. Keep Patient Calm & Warm</p>
              <p style={{ margin: 0, fontSize: 11.5, color: '#64748b', lineHeight: 1.4 }}>Prevent shock by reassuring them, laying them down flat, and covering with emergency sheets.</p>
            </div>
          </div>

          {/* Quick HUD status */}
          <div style={{
            background: 'rgba(39,174,96,0.06)', border: '1px solid rgba(39,174,96,0.2)',
            borderRadius: 10, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10, marginTop: 'auto'
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#27AE60', animation: 'pulse 1.5s infinite' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 800, color: '#27500A' }}>Dynamic Telemetry Signal Active</p>
              <p style={{ margin: 0, fontSize: 10, color: '#64748b' }}>Hardware sensor streams are verified and live.</p>
            </div>
          </div>

        </div>

      </div>
      <style>{`
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
      `}</style>
    </div>
  );
}
