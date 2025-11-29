import TelegramBot, { InlineKeyboardButton } from 'node-telegram-bot-api';
import express, { Request, Response } from 'express';
import axios from 'axios';

const token = process.env.TELEGRAM_TOKEN;
const bot = new TelegramBot(token, { polling: true });
const selectionState: Map<string, { productId: string; productUrl: string; name: string; sizes: string[]; selected: Set<string> }> = new Map();

const buildKeyboard = (state: { sizes: string[]; selected: Set<string>; productId: string; productUrl: string }): InlineKeyboardButton[][] => {
    const rows = state.sizes.map((size) => {
        const checked = state.selected.has(size) ? '✅' : '⬜';
        return [
            {
                text: `${checked} ${size}`,
                // Keep callback data small; Telegram limit is 64 bytes.
                callback_data: JSON.stringify({ t: 'size', pid: state.productId, s: size })
            }
        ];
    });
    rows.push([
        {
            text: 'Confirm',
            callback_data: JSON.stringify({ t: 'confirm', pid: state.productId })
        }
    ]);
    return rows;
};

// Handle "/add" command - Add user to the list
bot.onText(/\/add (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const url = match[1];
    const data = {
        url: url
    };
    console.log(`Adding:\n\tChatID: ${chatId}\n\tURL: ${url}`);
    try {
        const response = await axios.post(`http://api-connect:5508/follow/${chatId}`, data);
        const payload = response.data;

        if (payload.requires_size_selection) {
            const { sizes, product } = payload;
            const key = `${chatId}:${product.productId}`;
            const state = { productId: product.productId, productUrl: product.url, name: product.name, sizes, selected: new Set<string>() };
            selectionState.set(key, state);

            await bot.sendMessage(chatId, `Select sizes for ${product.name}:`, {
                reply_markup: { inline_keyboard: buildKeyboard(state) }
            });
            return;
        }

        await bot.sendMessage(chatId, JSON.stringify(payload));
    } catch (error) {
        await bot.sendMessage(chatId, 'Error adding product.');
    }
});

bot.on('callback_query', async (query) => {
    if (!query.data || !query.message) return;
    const chatId = query.message.chat.id;
    let data: any;
    try {
        data = JSON.parse(query.data);
    } catch {
        return;
    }
    if (data.t !== 'size' && data.t !== 'confirm') return;

    const key = `${chatId}:${data.pid}`;
    const state = selectionState.get(key);
    if (!state) {
        await bot.answerCallbackQuery(query.id, { text: 'Session expired. Please /add the product again.' });
        return;
    }

    if (data.t === 'size') {
        if (state.selected.has(data.s)) {
            state.selected.delete(data.s);
        } else {
            state.selected.add(data.s);
        }
        selectionState.set(key, state);
        const selectedText = state.selected.size ? `Selected: ${Array.from(state.selected).join(', ')}` : 'Select sizes:';
        await bot.answerCallbackQuery(query.id);
        await bot.editMessageText(`${selectedText}`, {
            chat_id: query.message.chat.id,
            message_id: query.message.message_id,
            reply_markup: { inline_keyboard: buildKeyboard(state) }
        });
        return;
    }

    if (data.t === 'confirm') {
        const sizes = Array.from(state.selected);
        // Persist the selection and close keyboard
        try {
            await axios.post(`http://api-connect:5508/follow/${chatId}`, {
                url: state.productUrl,
                sizes
            });
            await bot.answerCallbackQuery(query.id, { text: 'Saved!' });
            await bot.editMessageText(
                sizes.length ? `Tracking sizes: ${sizes.join(', ')}` : 'No sizes selected.',
                {
                    chat_id: query.message.chat.id,
                    message_id: query.message.message_id,
                    reply_markup: { inline_keyboard: [] }
                }
            );
        } catch (err) {
            console.error('Failed to persist sizes', err);
            await bot.answerCallbackQuery(query.id, { text: 'Failed to save. Try again.' });
        }
        return;
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
