const admin = require('firebase-admin');
const serviceAccount = require('./scripts/serviceAccountKey.json');

admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

async function listAll() {
    const collections = await db.listCollections();
    console.log('Top-level collections:');
    collections.forEach(c => console.log(' - ' + c.id));
    process.exit(0);
}

listAll().catch(e => {
    console.error(e);
    process.exit(1);
});
