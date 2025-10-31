const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
require('dotenv').config();

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const ADMIN_ID = process.env.ADMIN_USER_ID;
const bot = new TelegramBot(TOKEN, { polling: true });

// Carregar dados
const db = JSON.parse(fs.readFileSync('database.json', 'utf8'));
const config = JSON.parse(fs.readFileSync('config.json', 'utf8'));
const products = JSON.parse(fs.readFileSync('products.json', 'utf8'));

console.log('👑 Painel Administrativo Iniciado!');

function saveDB() {
    fs.writeFileSync('database.json', JSON.stringify(db, null, 2));
}

function saveConfig() {
    fs.writeFileSync('config.json', JSON.stringify(config, null, 2));
}

function saveProducts() {
    fs.writeFileSync('products.json', JSON.stringify(products, null, 2));
}

// ========== TECLADOS ADMIN ==========
const adminMainKeyboard = {
    reply_markup: {
        keyboard: [
            ['⚙️ CONFIGURAÇÕES GERAIS', '🕵️‍♀️ CONFIGURAR ADMINS'],
            ['👥 CONFIGURAR AFILIADOS', '👤 CONFIGURAR USUARIOS'],
            ['💠 CONFIGURAR PIX', '🖥️ CONFIGURAR LOGINS'],
            ['🔎 CONFIGURAR PESQUISA', '📊 ESTATÍSTICAS']
        ],
        resize_keyboard: true
    }
};

const configKeyboard = {
    reply_markup: {
        keyboard: [
            ['♻️ RENOVAR PLANO', '🤖 REINICIAR BOT'],
            ['🔴 MANUTENÇÃO', '🎧 MUDAR SUPORTE'],
            ['✂️ MUDAR SEPARADOR', '📭 MUDAR DESTINO LOG'],
            ['↩️ VOLTAR']
        ],
        resize_keyboard: true
    }
};

// ========== VERIFICAR ADMIN ==========
function isAdmin(userId) {
    return db.admins.includes(userId.toString());
}

// ========== COMANDO ADMIN ==========
bot.onText(/\/admin/, (msg) => {
    const chatId = msg.chat.id;
    
    if (!isAdmin(chatId)) {
        bot.sendMessage(chatId, "❌ Acesso negado. Apenas administradores podem usar este comando.");
        return;
    }
    
    const stats = calculateStats();
    
    const adminPanel = `👑 *PAINEL ADMINISTRATIVO*

⚙️ *DASHBOARD* ${config.bot.name}
📅 *Vencimento:* Indefinido
👑 *Vip:* Ativo
🤖 *Software version:* ${config.bot.version}

*📔 Métrica do Business*
📊 *Users:* ${Object.keys(db.users).length}
📈 *Receita total:* R$ ${stats.totalRevenue}
🗓️ *Receita mensal:* R$ ${stats.monthlyRevenue}
💠 *Receita de hoje:* R$ ${stats.todayRevenue}
🥇 *Vendas total:* ${stats.totalSales}
🏆 *Vendas hoje:* ${stats.todaySales}

🔧 *Use os botões abaixo para me configurar*`;
    
    bot.sendMessage(chatId, adminPanel, {
        parse_mode: 'Markdown',
        ...adminMainKeyboard
    });
});

function calculateStats() {
    let totalRevenue = 0;
    let monthlyRevenue = 0;
    let todayRevenue = 0;
    let totalSales = 0;
    let todaySales = 0;
    
    const today = new Date().toDateString();
    
    Object.values(db.users).forEach(user => {
        user.deposits.forEach(deposit => {
            if (deposit.status === 'completed') {
                totalRevenue += deposit.amount;
                
                const depositDate = new Date(deposit.date).toDateString();
                if (depositDate === today) {
                    todayRevenue += deposit.amount;
                }
                
                // Calcular receita mensal (simplificado)
                const depositMonth = new Date(deposit.date).getMonth();
                const currentMonth = new Date().getMonth();
                if (depositMonth === currentMonth) {
                    monthlyRevenue += deposit.amount;
                }
            }
        });
        
        totalSales += user.purchases.length;
        
        user.purchases.forEach(purchase => {
            const purchaseDate = new Date(purchase.date).toDateString();
            if (purchaseDate === today) {
                todaySales++;
            }
        });
    });
    
    return {
        totalRevenue: totalRevenue.toFixed(2),
        monthlyRevenue: monthlyRevenue.toFixed(2),
        todayRevenue: todayRevenue.toFixed(2),
        totalSales,
        todaySales
    };
}

// ========== CONFIGURAÇÕES GERAIS ==========
bot.onText(/⚙️ CONFIGURAÇÕES GERAIS/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    const configPanel = `🔧 *MENU DE CONFIGURAÇÕES DO BOT*

👮‍♀️ *Admin:* ${db.admins.length} administradores
💼 *Dono:* Principal

*Configurações atuais:*
📭 *Destino das LOG'S:* ${db.settings.logs_destination || 'Não configurado'}
👤 *Link do suporte atual:* ${db.settings.support_link}
✂️ *Separador:* ${config.separator}

*Exemplo do separador em ação:*
NOME${config.separator}VALOR`;
    
    bot.sendMessage(chatId, configPanel, {
        parse_mode: 'Markdown',
        ...configKeyboard
    });
});

// ========== MANUTENÇÃO ==========
bot.onText(/🔴 MANUTENÇÃO/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    const currentStatus = db.settings.maintenance ? 'ON' : 'OFF';
    const newStatus = !db.settings.maintenance;
    
    db.settings.maintenance = newStatus;
    saveDB();
    
    bot.sendMessage(chatId, `🔧 *Modo manutenção ${newStatus ? 'ativado' : 'desativado'}!*

O bot está agora ${newStatus ? 'em manutenção' : 'operacional'}.`, {
        parse_mode: 'Markdown',
        ...configKeyboard
    });
});

// ========== CONFIGURAR ADMINS ==========
bot.onText(/🕵️‍♀️ CONFIGURAR ADMINS/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    const adminPanel = `🅰️ *PAINEL CONFIGURAR ADMIN*

👮 *Administradores:* ${db.admins.length}

*Lista de administradores:*
${db.admins.map((admin, index) => `${index + 1}. ${admin}`).join('\n')}

*Use os botões abaixo para fazer as alterações necessárias:*`;

    const adminConfigKeyboard = {
        reply_markup: {
            keyboard: [
                ['➕ ADICIONAR ADM', '🚮 REMOVER ADM'],
                ['🗞️ LISTA DE ADM', '↩️ VOLTAR']
            ],
            resize_keyboard: true
        }
    };
    
    bot.sendMessage(chatId, adminPanel, {
        parse_mode: 'Markdown',
        ...adminConfigKeyboard
    });
});

// ========== ADICIONAR ADMIN ==========
bot.onText(/➕ ADICIONAR ADM/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    bot.sendMessage(chatId, `👮 *Adicionar Administrador*

Envie o ID do usuário que deseja tornar administrador:

*Exemplo:* 123456789`, {
        parse_mode: 'Markdown'
    });
});

// Processar adição de admin
bot.on('message', (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    
    if (!isAdmin(chatId)) return;
    
    // Verificar se é um ID numérico (provável adição de admin)
    if (/^\d+$/.test(text) && text.length >= 8) {
        const newAdminId = text;
        
        if (db.admins.includes(newAdminId)) {
            bot.sendMessage(chatId, `❌ O usuário ${newAdminId} já é administrador.`);
            return;
        }
        
        db.admins.push(newAdminId);
        saveDB();
        
        bot.sendMessage(chatId, `✅ *Administrador adicionado com sucesso!*

👮 *Novo admin ID:* ${newAdminId}
📊 *Total de admins:* ${db.admins.length}`, {
            parse_mode: 'Markdown',
            ...adminMainKeyboard
        });
    }
});

// ========== CONFIGURAR AFILIADOS ==========
bot.onText(/👥 CONFIGURAR AFILIADOS/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    const affiliateConfig = `🎗️ *CONFIGURAR SISTEMA DE AFILIADOS*

🔻 *Pontos mínimo para saldo:* ${config.affiliate.min_points}
✖️ *Multiplicador:* ${config.affiliate.multiplier}

👥 *SISTEMA DE INDICAÇÃO*

Ao clicar, altera o status do sistema de indicação. Se tiver OFF os usuários não poderão trocar seus pontos por saldo.

*Status atual:* ${config.affiliate.enabled ? '🟢 ON' : '🔴 OFF'}

🗞️ *Pontos por recarga:* ${config.affiliate.points_per_recharge}

🔻 *Pontos mínimo para converter:* ${config.affiliate.min_points}

✖️ *Multiplicador para converter:* ${config.affiliate.multiplier}

*Exemplo:* Se o multiplicador for ${config.affiliate.multiplier} e o usuário tiver ${config.affiliate.min_points} pontos, quando converter ficará com R$ ${(config.affiliate.min_points * config.affiliate.multiplier).toFixed(2)} de saldo.`;

    const affiliateKeyboard = {
        reply_markup: {
            keyboard: [
                [config.affiliate.enabled ? '🔴 DESATIVAR SISTEMA' : '🟢 ATIVAR SISTEMA'],
                ['🗞️ PONTOS POR RECARGA', '🔻 PONTOS MINIMO'],
                ['✖️ MULTIPLICADOR', '↩️ VOLTAR']
            ],
            resize_keyboard: true
        }
    };
    
    bot.sendMessage(chatId, affiliateConfig, {
        parse_mode: 'Markdown',
        ...affiliateKeyboard
    });
});

// ========== ATIVAR/DESATIVAR AFILIADOS ==========
bot.onText(/🟢 ATIVAR SISTEMA|🔴 DESATIVAR SISTEMA/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    config.affiliate.enabled = !config.affiliate.enabled;
    saveConfig();
    
    bot.sendMessage(chatId, `✅ *Sistema de afiliados ${config.affiliate.enabled ? 'ativado' : 'desativado'}!*

Os usuários ${config.affiliate.enabled ? 'agora podem' : 'não podem mais'} trocar pontos por saldo.`, {
        parse_mode: 'Markdown'
    });
});

// ========== CONFIGURAR PRODUTOS ==========
bot.onText(/🖥️ CONFIGURAR LOGINS/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    let totalStock = 0;
    Object.keys(products).forEach(category => {
        products[category].forEach(product => {
            totalStock += product.stock;
        });
    });
    
    const productsConfig = `📦 *CONFIGURAR LOGINS/PRODUTOS*

📊 *Logins no estoque:* ${totalStock}

*Opções disponíveis:*`;

    const productsKeyboard = {
        reply_markup: {
            keyboard: [
                ['📮 ADICIONAR LOGIN', '🥾 REMOVER LOGIN'],
                ['❌ REMOVER POR PLATAFORMA', '📦 ESTOQUE DETALHADO'],
                ['🗑️ ZERAR ESTOQUE', '💸 MUDAR VALOR'],
                ['🪪 MUDAR VALOR TODOS', '↩️ VOLTAR']
            ],
            resize_keyboard: true
        }
    };
    
    bot.sendMessage(chatId, productsConfig, {
        parse_mode: 'Markdown',
        ...productsKeyboard
    });
});

// ========== ADICIONAR PRODUTO ==========
bot.onText(/📮 ADICIONAR LOGIN/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    const example = `NOME${config.separator}VALOR${config.separator}DESCRICAO${config.separator}EMAIL${config.separator}SENHA${config.separator}DURACAO`;
    
    bot.sendMessage(chatId, `📮 *ADICIONAR LOGINS*

Envie os logins no formato:

\`\`\`
${example}
\`\`\`

*Para múltiplos logins, envie um por linha.*

*Exemplo prático:*
\`\`\`
Netflix Premium${config.separator}29.90${config.separator}Acesso Netflix Premium${config.separator}user@email.com${config.separator}senha123${config.separator}30
Spotify${config.separator}14.90${config.separator}Acesso Spotify Premium${config.separator}user2@email.com${config.separator}senha456${config.separator}60
\`\`\``, {
        parse_mode: 'Markdown'
    });
});

// Processar adição de produtos
let waitingForProducts = false;

bot.on('message', (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    
    if (!isAdmin(chatId)) return;
    
    // Verificar se é formato de produto
    if (text.includes(config.separator) && text.split(config.separator).length >= 6) {
        addProductFromText(chatId, text);
    }
});

function addProductFromText(chatId, text) {
    const lines = text.split('\n');
    let addedCount = 0;
    
    lines.forEach(line => {
        if (line.includes(config.separator)) {
            const parts = line.split(config.separator);
            if (parts.length >= 6) {
                const [name, price, description, email, password, duration] = parts;
                
                // Criar categoria padrão se não existir
                if (!products['Logins']) {
                    products['Logins'] = [];
                }
                
                // Adicionar produto
                products['Logins'].push({
                    name: name.trim(),
                    price: parseFloat(price),
                    description: description.trim(),
                    credentials: {
                        email: email.trim(),
                        password: password.trim()
                    },
                    warranty: parseInt(duration),
                    stock: 1,
                    category: 'Logins'
                });
                
                addedCount++;
            }
        }
    });
    
    saveProducts();
    
    bot.sendMessage(chatId, `✅ *${addedCount} produtos adicionados com sucesso!*

📦 *Total no estoque:* ${Object.keys(products).reduce((acc, cat) => acc + products[cat].length, 0)} produtos`, {
        parse_mode: 'Markdown',
        ...adminMainKeyboard
    });
}

// ========== ESTATÍSTICAS ==========
bot.onText(/📊 ESTATÍSTICAS/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    const stats = calculateStats();
    const userStats = calculateUserStats();
    
    const statistics = `📊 *ESTATÍSTICAS DETALHADAS*

*💰 FINANCEIRO*
📈 Receita total: R$ ${stats.totalRevenue}
🗓️ Receita mensal: R$ ${stats.monthlyRevenue}
💠 Receita hoje: R$ ${stats.todayRevenue}

*👥 USUÁRIOS*
📊 Total usuários: ${Object.keys(db.users).length}
🆕 Novos hoje: ${userStats.newToday}
📈 Crescimento: ${userStats.growth}%

*🛒 VENDAS*
🥇 Vendas total: ${stats.totalSales}
🏆 Vendas hoje: ${stats.todaySales}
📦 Produtos em estoque: ${Object.keys(products).reduce((acc, cat) => acc + products[cat].length, 0)}

*🎗️ AFILIADOS*
👥 Total afiliados: ${Object.keys(db.users).filter(id => db.users[id].affiliate.referrals.length > 0).length}
💰 Comissões pagas: R$ ${userStats.totalCommissions.toFixed(2)}`;

    bot.sendMessage(chatId, statistics, {
        parse_mode: 'Markdown',
        ...adminMainKeyboard
    });
});

function calculateUserStats() {
    const today = new Date().toDateString();
    let newToday = 0;
    let totalCommissions = 0;
    
    Object.values(db.users).forEach(user => {
        const regDate = new Date(user.registered_at).toDateString();
        if (regDate === today) {
            newToday++;
        }
        
        // Calcular comissões (simplificado)
        totalCommissions += user.affiliate.points * config.affiliate.multiplier;
    });
    
    const growth = Object.keys(db.users).length > 0 ? 
        (newToday / Object.keys(db.users).length * 100).toFixed(1) : 0;
    
    return {
        newToday,
        growth,
        totalCommissions
    };
}

// ========== VOLTAR ==========
bot.onText(/↩️ VOLTAR/, (msg) => {
    const chatId = msg.chat.id;
    if (!isAdmin(chatId)) return;
    
    bot.sendMessage(chatId, "👑 *Painel Administrativo*", {
        parse_mode: 'Markdown',
        ...adminMainKeyboard
    });
});

console.log('✅ Painel administrativo rodando!');
