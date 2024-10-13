const fs = require('fs');
const { fork } = require('child_process');

const csvData = fs.readFileSync('authorization.csv', 'utf8');
const authorizationList = csvData.split('\n').map(line => line.trim()).filter(line => line !== '' && !line.includes('#'));

function startWorker(authorization, name) {
    const worker = fork('hamster-v3.js', [authorization, name]);

    worker.on('message', (msg) => {
        console.log(`Message from ${name}: ${msg}`);
    });

    worker.on('exit', (code) => {
        console.log(`Worker ${name} exited with code ${code}`);
    });

    worker.on('error', (err) => {
        console.error(`Worker ${name} encountered an error:`, err);
    });
}

function main() {
    authorizationList.forEach((authorization, index) => {
        const [token, name] = authorization.split(':');
        startWorker(token, name || `acc${index + 1}`);
    });
    console.log('All workers started');
}

main();
