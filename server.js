const mqtt = require('mqtt');
const express = require('express');
const cookieParser = require('cookie-parser');
const bcrypt = require('bcrypt');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = 3000;
const UPLOAD_DIR = path.join(__dirname, 'uploads');
const mqttClient = mqtt.connect('mqtt://localhost:1883');

// Ensure uploads directory exists
if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR);

// Session tracking
const sessions = new Set();

// Load user credentials (bcrypt hashes)
const USERS = fs.existsSync('users.json')
  ? JSON.parse(fs.readFileSync('users.json', 'utf8'))
  : {};

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// MQTT message handling
mqttClient.on('connect', () => {
  console.log('MQTT connected. Subscribing to topic rfid/coop');
  mqttClient.subscribe('rfid/coop');
});

mqttClient.on('message', (topic, message) => {
  try {
    const entry = JSON.parse(message.toString());
    const date = entry.timestamp.split(' ')[0]; // YYYY-MM-DD
    const filename = path.join(UPLOAD_DIR, `${date}.csv`);
    const isNew = !fs.existsSync(filename);
    const csvLine = `${entry.timestamp},${entry.antenna},${entry.eid},${entry.device}\n`;

    if (isNew) {
      fs.writeFileSync(filename, 'timestamp,antenna,eid,device\n' + csvLine);
    } else {
      fs.appendFileSync(filename, csvLine);
    }
  } catch (err) {
    console.error('Failed to parse MQTT message:', err.message);
  }
});

// Authentication helpers
function isAuthenticated(req) {
  return sessions.has(req.cookies.session);
}
function requireAuth(req, res, next) {
  if (!isAuthenticated(req)) return res.redirect('/login');
  next();
}

// Login routes
app.get('/login', (req, res) => {
  res.send(`
    <h2>Login</h2>
    <form method="POST" action="/login">
      Username: <input name="username"><br>
      Password: <input type="password" name="password"><br>
      <button type="submit">Login</button>
    </form>
  `);
});

app.post('/login', async (req, res) => {
  const { username, password } = req.body;
  const hash = USERS[username];
  if (!hash || !(await bcrypt.compare(password, hash))) {
    return res.status(403).send('Invalid credentials');
  }

  const sessionId = crypto.randomBytes(16).toString('hex');
  sessions.add(sessionId);
  res.cookie('session', sessionId, { httpOnly: true });
  res.redirect('/data');
});

// File list UI
app.get('/data', requireAuth, (req, res) => {
  const files = fs.readdirSync(UPLOAD_DIR)
    .filter(f => f.endsWith('.csv'))
    .sort()
    .reverse();
  console.log(files)
  const list = files.map(f => `<li><a href="/download/${f}">${f}</a></li>`).join('');
  res.send(`<h2>Download Daily CSV Files</h2><ul>${list}</ul>`);
});

// File download
app.get('/download/:filename', requireAuth, (req, res) => {
  const file = path.join(UPLOAD_DIR, req.params.filename);
  if (fs.existsSync(file)) {
    res.download(file);
  } else {
    res.status(404).send('File not found');
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Web interface on http://localhost:${PORT}/data`);
});
