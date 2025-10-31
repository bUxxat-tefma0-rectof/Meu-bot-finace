const TelegramBot = require('node-telegram-bot-api');
const { OpenAI } = require('openai');
const axios = require('axios');
const FormData = require('form-data');
require('dotenv').config();

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const OPENAI_KEY = process.env.OPENAI_API_KEY;

const bot = new TelegramBot(TOKEN, { polling: true });
const openai = new OpenAI({ apiKey: OPENAI_KEY });

console.log('🤖 Bot Inteligente com ChatGPT iniciado!');

// Função para chamar ChatGPT
async function askGPT(prompt) {
  try {
    const response = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [
        {
          role: "system",
          content: `Você é um assistente financeiro inteligente. Analise transações, categorize gastos, dê conselhos financeiros e responda de forma útil e detalhada. 
          Sempre que identificar valores monetários, categorize automaticamente.`
        },
        {
          role: "user",
          content: prompt
        }
      ],
      max_tokens: 500
    });

    return response.choices[0].message.content;
  } catch (error) {
    console.error('Erro ChatGPT:', error);
    return "❌ Erro ao processar sua mensagem. Tente novamente!";
  }
}

// Processar áudio usando Whisper (OpenAI)
async function transcribeAudio(audioUrl) {
  try {
    // Baixar áudio
    const response = await axios.get(audioUrl, { responseType: 'arraybuffer' });
    const audioBuffer = Buffer.from(response.data);

    // Transcrever com Whisper
    const transcription = await openai.audio.transcriptions.create({
      file: audioBuffer,
      model: "whisper-1",
      language: "pt"
    });

    return transcription.text;
  } catch (error) {
    console.error('Erro transcrição:', error);
    return null;
  }
}

// Processar imagem usando GPT-4 Vision
async function analyzeImage(imageUrl) {
  try {
    const response = await openai.chat.completions.create({
      model: "gpt-4-vision-preview",
      messages: [
        {
          role: "user",
          content: [
            {
              type: "text",
              text: "Analise esta imagem e extraia todas as informações financeiras: valores, descrições, datas, categorias. Se for um comprovante, nota fiscal ou extrato, me diga os detalhes financeiros."
            },
            {
              type: "image_url",
              image_url: { url: imageUrl }
            }
          ]
        }
      ],
      max_tokens: 500
    });

    return response.choices[0].message.content;
  } catch (error) {
    console.error('Erro análise imagem:', error);
    return null;
  }
}

// BOTÕES INTELIGENTES
const mainKeyboard = {
  reply_markup: {
    keyboard: [
      ['💸 Registrar Gasto', '💰 Registrar Receita'],
      ['📊 Analisar Gastos', '💡 Dicas Financeiras'],
      ['📈 Relatório Mensal', '🎯 Metas Financeiras']
    ],
    resize_keyboard: true
  }
};

// COMANDO START
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  
  const welcome = await askGPT(`Crie uma mensagem de boas-vindas para um bot financeiro inteligente. Seja caloroso e explique que posso:
  - Analisar gastos por áudio, imagem ou texto
  - Dar conselhos financeiros
  - Categorizar automaticamente
  - Criar relatórios
  - Ajudar com metas financeiras`);
  
  bot.sendMessage(chatId, welcome, mainKeyboard);
});

// PROCESSAR MENSAGENS DE TEXTO
bot.on('message', async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  // Ignorar comandos e mensagens vazias
  if (!text || text.startsWith('/')) return;

  try {
    // Enviar mensagem de "digitando..."
    await bot.sendChatAction(chatId, 'typing');

    let response;

    // Processar baseado no tipo de mensagem
    if (msg.voice) {
      // 🎤 PROCESSAR ÁUDIO
      await bot.sendMessage(chatId, "🎤 Convertendo áudio em texto...");
      const fileLink = await bot.getFileLink(msg.voice.file_id);
      const transcribedText = await transcribeAudio(fileLink);
      
      if (transcribedText) {
        await bot.sendMessage(chatId, `📝 Áudio convertido: "${transcribedText}"`);
        response = await askGPT(`Analise esta transação de áudio: "${transcribedText}". 
        Categorize, identifique valor, tipo (receita/despesa) e dê conselhos se for gasto.`);
      } else {
        response = "❌ Não consegui entender o áudio. Tente novamente!";
      }

    } else if (msg.photo) {
      // 📷 PROCESSAR IMAGEM
      await bot.sendMessage(chatId, "📷 Analisando imagem...");
      const fileLink = await bot.getFileLink(msg.photo[msg.photo.length - 1].file_id);
      const imageAnalysis = await analyzeImage(fileLink);
      
      if (imageAnalysis) {
        response = await askGPT(`Analise estas informações extraídas de uma imagem: "${imageAnalysis}". 
        Organize como transação financeira e dê insights.`);
      } else {
        response = "❌ Não consegui analisar a imagem. Tente outra!";
      }

    } else {
      // 💬 PROCESSAR TEXTO NORMAL
      response = await askGPT(`Analise esta mensagem do usuário: "${text}". 
      Se for uma transação financeira, categorize, identifique valor, tipo e dê conselhos. 
      Se for pergunta financeira, responda de forma útil. Se for outra coisa, seja prestativo.`);
    }

    // Enviar resposta
    await bot.sendMessage(chatId, response, mainKeyboard);

  } catch (error) {
    console.error('Erro geral:', error);
    bot.sendMessage(chatId, "❌ Erro ao processar. Tente novamente!", mainKeyboard);
  }
});

// COMANDOS ESPECÍFICOS
bot.onText(/\/analisar/, async (msg) => {
  const chatId = msg.chat.id;
  const response = await askGPT("Analise os gastos do usuário e dê um resumo geral com conselhos para economizar.");
  bot.sendMessage(chatId, response, mainKeyboard);
});

bot.onText(/\/dicas/, async (msg) => {
  const chatId = msg.chat.id;
  const response = await askGPT("Dê 5 dicas financeiras práticas para o usuário melhorar suas finanças pessoais.");
  bot.sendMessage(chatId, response, mainKeyboard);
});

bot.onText(/\/relatorio/, async (msg) => {
  const chatId = msg.chat.id;
  const response = await askGPT("Crie um relatório financeiro mensal fictício com: receitas, despesas por categoria, saldo e metas para o próximo mês.");
  bot.sendMessage(chatId, response, mainKeyboard);
});

console.log('✅ Bot rodando perfeitamente!');
