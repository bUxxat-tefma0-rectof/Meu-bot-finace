const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const ADMIN_ID = process.env.ADMIN_USER_ID;
const bot = new TelegramBot(TOKEN, { polling: true });

// Carregar dados
const db = JSON.parse(fs.readFileSync('database.json', 'utf8'));
const config = JSON.parse(fs.readFileSync('config.json', 'utf8'));
const products = JSON.parse(fs.readFileSync('products.json', 'utf8'));

console.log('🤖 Bot de Vendas Iniciado!');

// ========== FUNÇÕES AUXILIARES ==========
function saveDB() {
    fs.writeFileSync('database.json', JSON.stringify(db, null, 2));
}

function saveProducts() {
    fs.writeFileSync('products.json', JSON.stringify(products, null, 2));
}

function getUser(chatId) {
    if (!db.users[chatId]) {
        db.users[chatId] = {
            id: chatId,
            balance: 0,
            purchases: [],
            deposits: [],
            gifts: [],
            affiliate: {
                code: generateAffiliateCode(),
                points: 0,
                referrals: []
            },
            registered_at: new Date().toISOString()
        };
        saveDB();
    }
    return db.users[chatId];
}

function generateAffiliateCode() {
    return Math.random().toString(36).substring(2, 8).toUpperCase();
}

// ========== TECLADOS ==========
const mainKeyboard = {
    reply_markup: {
        keyboard: [
            ['💎 Logins | Contas Premium', '🪪 Perfil'],
            ['💰 Recarga', '🎖️ Ranking'],
            ['👩‍💻 Suporte', 'ℹ️ Informações'],
            ['🔎 Pesquisar Serviços']
        ],
        resize_keyboard: true
    }
};

const profileKeyboard = {
    reply_markup: {
        keyboard: [
            ['🛍️ Histórico de Compras', '↩️ Voltar']
        ],
        resize_keyboard: true
    }
};

const backKeyboard = {
    reply_markup: {
        keyboard: [
            ['↩️ Voltar']
        ],
        resize_keyboard: true
    }
};

// ========== COMANDOS PRINCIPAIS ==========
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const user = getUser(chatId);
    
    const welcome = `🥇 *Descubra como nosso bot pode transformar sua experiência de compras!*

Ele facilita a busca por diversos produtos e serviços, garantindo que você encontre o que precisa com o melhor preço e excelente custo-benefício.

*Importante:* Não realizamos reembolsos em dinheiro. O suporte estará disponível por até 48 horas após a entrega das informações, com reembolso em créditos no bot, se necessário.

👥 *Grupo De Clientes:* ${config.bot.group_link}
👨‍💻 *Link De Suporte:* ${config.bot.support_link}

*ℹ️ Seus Dados:*
🆔 *ID:* ${user.id}
💸 *Saldo Atual:* R$ ${user.balance.toFixed(2)}
🪪 *Usuário:* ${msg.from.first_name}`;

    bot.sendMessage(chatId, welcome, {
        parse_mode: 'Markdown',
        ...mainKeyboard
    });
});

// ========== MENU PERFIL ==========
bot.onText(/🪪 Perfil/, (msg) => {
    const chatId = msg.chat.id;
    const user = getUser(chatId);
    
    const profile = `🙋‍♂️ *Meu Perfil*

🔎 *Veja aqui os detalhes da sua conta:*

*👤 Informações:*
🆔 *ID da Carteira:* ${user.id}
💰 *Saldo Atual:* R$ ${user.balance.toFixed(2)}

*📊 Suas movimentações:*
— 🛒 Compras Realizadas: ${user.purchases.length}
— 💠 Pix Inseridos: ${user.deposits.length}
— 🎁 Gifts Resgatados: R$ ${user.gifts.reduce((acc, g) => acc + g.amount, 0).toFixed(2)}`;

    bot.sendMessage(chatId, profile, {
        parse_mode: 'Markdown',
        ...profileKeyboard
    });
});

// ========== HISTÓRICO DE COMPRAS ==========
bot.onText(/🛍️ Histórico de Compras/, (msg) => {
    const chatId = msg.chat.id;
    const user = getUser(chatId);
    
    let history = `*HISTÓRICO DETALHADO*
${config.bot.name}
_______________________

*COMPRAS:*
`;
    
    user.purchases.forEach((purchase, index) => {
        history += `\n${index + 1}. ${purchase.product} - R$ ${purchase.amount} - ${new Date(purchase.date).toLocaleDateString('pt-BR')}`;
    });
    
    history += `\n_______________________\n\n*PAGAMENTOS:*`;
    
    user.deposits.forEach((deposit, index) => {
        history += `\n${index + 1}. R$ ${deposit.amount} - ${new Date(deposit.date).toLocaleDateString('pt-BR')} - ${deposit.status}`;
    });
    
    // Enviar como arquivo de texto
    const filename = `historico_${chatId}.txt`;
    fs.writeFileSync(filename, history);
    
    bot.sendDocument(chatId, filename, {
        caption: '📊 Seu histórico de compras e pagamentos'
    }).then(() => {
        fs.unlinkSync(filename);
    });
});

// ========== SISTEMA DE RECARGA ==========
bot.onText(/💰 Recarga/, (msg) => {
    const chatId = msg.chat.id;
    const user = getUser(chatId);
    
    const recharge = `💼 | *ID da Carteira:* ${user.id}
💵 | *Saldo Disponível:* R$ ${user.balance.toFixed(2)}

💡 *Selecione uma opção para recarregar:*`;

    const rechargeKeyboard = {
        reply_markup: {
            keyboard: [
                ['💳 Stripe', '↩️ Voltar']
            ],
            resize_keyboard: true
        }
    };
    
    bot.sendMessage(chatId, recharge, {
        parse_mode: 'Markdown',
        ...rechargeKeyboard
    });
});

bot.onText(/💳 Stripe/, (msg) => {
    const chatId = msg.chat.id;
    
    bot.sendMessage(chatId, `ℹ️ *Informe o valor que deseja recarregar:*

🔻 *Recarga mínima:* R$ ${config.payments.min_deposit}
⚠️ *Por favor, envie o valor que deseja recarregar agora.*

*Exemplo:* 50 ou 37.50`, {
        parse_mode: 'Markdown'
    });
});

// Processar valor de recarga
bot.on('message', (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    
    // Verificar se é um número (valor de recarga)
    if (!isNaN(parseFloat(text)) && isFinite(text)) {
        const amount = parseFloat(text);
        
        if (amount < config.payments.min_deposit) {
            bot.sendMessage(chatId, `❌ *Valor abaixo do mínimo!*\n\nRecarga mínima: R$ ${config.payments.min_deposit}`, {
                parse_mode: 'Markdown'
            });
            return;
        }
        
        if (amount > config.payments.max_deposit) {
            bot.sendMessage(chatId, `❌ *Valor acima do máximo!*\n\nRecarga máxima: R$ ${config.payments.max_deposit}`, {
                parse_mode: 'Markdown'
            });
            return;
        }
        
        // Simular processamento Stripe
        processStripePayment(chatId, amount);
    }
});

function processStripePayment(chatId, amount) {
    const user = getUser(chatId);
    
    bot.sendMessage(chatId, "⏳ *Gerando pagamento...*", { parse_mode: 'Markdown' });
    
    // Simular processamento
    setTimeout(() => {
        // Adicionar saldo
        user.balance += amount;
        user.deposits.push({
            amount: amount,
            date: new Date().toISOString(),
            method: 'stripe',
            status: 'completed'
        });
        
        saveDB();
        
        const successMsg = `✅ *Pagamento confirmado!*

💸 *Valor recarregado:* R$ ${amount.toFixed(2)}
💰 *Novo saldo:* R$ ${user.balance.toFixed(2)}

Obrigado pela recarga! 🎉`;
        
        bot.sendMessage(chatId, successMsg, {
            parse_mode: 'Markdown',
            ...mainKeyboard
        });
    }, 3000);
}

// ========== SISTEMA DE PRODUTOS ==========
bot.onText(/💎 Logins \| Contas Premium/, (msg) => {
    const chatId = msg.chat.id;
    
    let productsList = `🎟️ *Logins Premium | Acesso Exclusivo*

🏦 *Carteira*
💸 *Saldo Atual:* R$ ${getUser(chatId).balance.toFixed(2)}

*Produtos disponíveis:*\n`;
    
    Object.keys(products).forEach(category => {
        productsList += `\n📁 *${category}*`;
        products[category].forEach(product => {
            productsList += `\n• ${product.name} - R$ ${product.price}`;
        });
    });
    
    const productsKeyboard = {
        reply_markup: {
            keyboard: [
                ...Object.keys(products).map(category => [category]),
                ['↩️ Voltar']
            ],
            resize_keyboard: true
        }
    };
    
    bot.sendMessage(chatId, productsList, {
        parse_mode: 'Markdown',
        ...productsKeyboard
    });
});

// ========== SISTEMA DE PESQUISA ==========
bot.onText(/🔎 Pesquisar Serviços/, (msg) => {
    const chatId = msg.chat.id;
    
    bot.sendMessage(chatId, `🔍 *Pesquisar Serviços*

Digite o nome do serviço que deseja procurar:

*Exemplo:* Netflix, Spotify, Disney+`, {
        parse_mode: 'Markdown'
    });
});

// Pesquisa de serviços
bot.on('message', (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    
    // Ignorar comandos e mensagens muito curtas
    if (text.startsWith('/') || text.length < 3) return;
    
    const searchResults = searchProducts(text);
    
    if (searchResults.length > 0) {
        let resultsText = `🔍 *Resultados para "${text}":*\n\n`;
        
        searchResults.forEach((product, index) => {
            resultsText += `${index + 1}. *${product.name}* - R$ ${product.price}\n`;
            resultsText += `   📦 Estoque: ${product.stock}\n`;
            resultsText += `   📝 ${product.description.substring(0, 50)}...\n\n`;
        });
        
        const productKeyboard = {
            reply_markup: {
                keyboard: [
                    ...searchResults.map(p => [p.name]),
                    ['↩️ Voltar']
                ],
                resize_keyboard: true
            }
        };
        
        bot.sendMessage(chatId, resultsText, {
            parse_mode: 'Markdown',
            ...productKeyboard
        });
    }
});

function searchProducts(query) {
    const results = [];
    const searchTerm = query.toLowerCase();
    
    Object.keys(products).forEach(category => {
        products[category].forEach(product => {
            if (product.name.toLowerCase().includes(searchTerm)) {
                results.push(product);
            }
        });
    });
    
    return results.slice(0, 5); // Limitar a 5 resultados
}

// ========== SISTEMA DE COMPRAS ==========
bot.on('message', (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    const user = getUser(chatId);
    
    // Verificar se é um produto válido
    const product = findProductByName(text);
    
    if (product) {
        showProductDetails(chatId, user, product);
    }
});

function findProductByName(name) {
    for (const category in products) {
        const product = products[category].find(p => p.name === name);
        if (product) return product;
    }
    return null;
}

function showProductDetails(chatId, user, product) {
    const productInfo = `⚜️ *ACESSO:* ${product.name}

💵 *Preço:* R$ ${product.price}
💼 *Saldo Atual:* R$ ${user.balance.toFixed(2)}
📥 *Estoque Disponível:* ${product.stock}

🗒️ *Descrição:* ${product.description}

*Aviso Importante:*
O acesso é disponibilizado na hora. Não atendemos ligações nem ouvimos mensagens de áudio; pedimos que aguarde sua vez.
Informamos que não realizamos reembolsos via Pix, apenas em créditos no bot, correspondendo aos dias restantes até o vencimento.
Agradecemos pela compreensão e desejamos boas compras!

♻️ *Garantia:* ${product.warranty} dias`;

    const buyKeyboard = {
        reply_markup: {
            keyboard: [
                ['🛒 Comprar', '↩️ Voltar']
            ],
            resize_keyboard: true
        }
    };
    
    bot.sendMessage(chatId, productInfo, {
        parse_mode: 'Markdown',
        ...buyKeyboard
    });
}

bot.onText(/🛒 Comprar/, (msg) => {
    const chatId = msg.chat.id;
    const user = getUser(chatId);
    
    // Aqui você implementaria a lógica de compra real
    // Por enquanto, vamos simular uma compra
    
    if (user.balance < 10) { // Exemplo de preço
        bot.sendMessage(chatId, `❌ *Saldo insuficiente!*

Faltam: R$ ${(10 - user.balance).toFixed(2)}
Seu saldo: R$ ${user.balance.toFixed(2)}

Faça uma recarga e tente novamente.`, {
            parse_mode: 'Markdown'
        });
        return;
    }
    
    // Simular compra bem-sucedida
    user.balance -= 10;
    user.purchases.push({
        product: "Produto Exemplo",
        amount: 10,
        date: new Date().toISOString()
    });
    
    saveDB();
    
    bot.sendMessage(chatId, `✅ *Compra realizada com sucesso!*

🛒 *Produto:* Produto Exemplo
💸 *Valor:* R$ 10,00
💰 *Saldo restante:* R$ ${user.balance.toFixed(2)}

📧 *Email:* exemplo@email.com
🔑 *Senha:* ********

Aproveite sua compra! 🎉`, {
        parse_mode: 'Markdown',
        ...mainKeyboard
    });
});

// ========== COMANDOS ADICIONAIS ==========
bot.onText(/\/afiliados/, (msg) => {
    const chatId = msg.chat.id;
    const user = getUser(chatId);
    
    const affiliateInfo = `🎗️ *Sistema de Afiliados*

*ℹ️ Status:* ${config.affiliate.enabled ? '🟢 ATIVO' : '🔴 INATIVO'}
📊 *Comissão por Indicação:* ${(config.affiliate.multiplier * 100)}%
👥 *Total de Afiliados:* ${user.affiliate.referrals.length}
🔗 *Link para Indicar:* https://t.me/${config.bot.name.replace('@', '')}?start=${user.affiliate.code}

*Como Funciona?*
Copie seu link de indicação e envie para outras pessoas.
Cada vez que alguém indicado por você fizer uma recarga no bot, você receberá uma porcentagem desse valor!

*Exemplo:* Com uma comissão de ${(config.affiliate.multiplier * 100)}%, se 5 pessoas indicadas recarregarem R$10,00 cada, você receberá R$ ${(5 * 10 * config.affiliate.multiplier).toFixed(2)}.

Indique mais e aumente seus ganhos! 💰`;
    
    bot.sendMessage(chatId, affiliateInfo, {
        parse_mode: 'Markdown'
    });
});

bot.onText(/\/id/, (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId, `🆔 *Seu ID é:* ${chatId}`, {
        parse_mode: 'Markdown'
    });
});

// ========== VOLTAR ==========
bot.onText(/↩️ Voltar/, (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId, "Menu principal:", mainKeyboard);
});

console.log('✅ Bot de vendas rodando perfeitamente!');
