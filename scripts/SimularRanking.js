// simularRanking.js
const admin = require("firebase-admin");

// Carrega as suas credenciais de administrador 
const serviceAccount = require("./serviceAccountKey.json");

// Inicializa a aplicação de admin do Firebase
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: `https://${serviceAccount.project_id}.firebaseio.com`
});

const db = admin.firestore();
const appId = "med-projeto";

// --- PARÂMETROS DA SIMULAÇÃO (Pode ajustar estes valores) ---
const NUM_USERS = 300; // Quantos utilizadores fictícios vamos criar
const MEAN_ACCURACY = 70.0; // A pontuação média (70%)
const STD_DEV = 15.0; // O desvio padrão (quão "espalhada" é a curva)
// -------------------------------------------------------------

/**
 * Gera um número aleatório seguindo uma distribuição normal (Curva de Gauss)
 * usando a transformada de Box-Muller.
 */
function generateNormalDistribution(mean, stdDev) {
  let u1 = 0, u2 = 0;
  while (u1 === 0) u1 = Math.random(); // Converte para (0,1]
  while (u2 === 0) u2 = Math.random(); // Converte para (0,1]
  const z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
  // Multiplica pelo desvio padrão e adiciona a média
  return z0 * stdDev + mean;
}

async function runSimulation() {
  console.log("A gerar dados de desempenho simulados...");

  const accuracies = [];
  for (let i = 0; i < NUM_USERS; i++) {
    let accuracy = generateNormalDistribution(MEAN_ACCURACY, STD_DEV);
    
    // Garante que a precisão está entre 0 e 100
    if (accuracy > 100) accuracy = 100;
    if (accuracy < 0) accuracy = 0;
    
    accuracies.push(accuracy);
  }

  console.log(`Geradas ${accuracies.length} pontuações de utilizadores.`);
  console.log("A enviar dados para o Firestore...");

  try {
    const distributionRef = db.doc(`artifacts/${appId}/statistics/performanceDistribution`);
    
    await distributionRef.set({
      accuracies: accuracies,
      lastUpdated: new Date(),
      isSimulation: true // Um campo para saber que estes dados são de teste
    });

    console.log("✅ Sucesso! Os dados simulados foram guardados no Firestore.");
    console.log("Pode agora recarregar a página 'desempenhoRanking' na sua aplicação.");

  } catch (error) {
    console.error("❌ Erro ao guardar dados no Firestore:", error);
  }
}

runSimulation();