import TelegramBot from 'node-telegram-bot-api';
import express, { Request, Response } from 'express';
import axios from 'axios';

const token = process.env.TELEGRAM_TOKEN;
const bot = new TelegramBot(token, { polling: true });

// Handle "/add" command - Add user to the list
bot.onText(/\/add (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const url = match[1];
    console.log(`Adding:\n\tChatID: ${chatId}\n\tURL: ${url}`);
    try {
        const response = await axios.post(`http://api-connect:5508/follow/${chatId}?url=${url}`);
        await bot.sendMessage(chatId, response.statusText);
    } catch (error) {
        await bot.sendMessage(chatId, error);
    }
});

// Handle "/list" command - List users by sending HTTP request to another service
bot.onText(/\/list/, async (msg) => {
    const chatId = msg.chat.id;
    try {
        const response = await axios.get(`http://api-connect:5508/follow/${chatId}`);
        const data = response.data
        await bot.sendMessage(chatId, `List of URLs: ${JSON.stringify(data)}`);
    } catch (error) {
        await bot.sendMessage(chatId, 'Error fetching the list.');
    }
});

// Express app to expose "event" API
const app = express();
app.use(express.json());

// API endpoint: /event - sends a message to all users
app.post('/event', (req: Request, res: Response) => {
    console.log(`Received event: ${req.body}`);
    const userId = req.body.userId;
    const message = req.body.message;
    bot.sendMessage(userId, message);
    res.send(`Message sent`)
});

app.listen(3000, () => {
    console.log('Bot API listening on port 3000');
});