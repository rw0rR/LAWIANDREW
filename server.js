/* LAWIANDREW CHAT - server.js (YENİLENMİŞ NİHAİ KOD - RENDER UYUMLU) */

const express = require('express');
const app = express();
const http = require('http'); // 1. DEĞİŞİKLİK: Standart http modülü çağrıldı
const server = http.createServer(app); // 1. DEĞİŞİKLİK: http sunucusu Express uygulamasına bağlandı
const { v4: uuidv4 } = require('uuid');

// 2. DEĞİŞİKLİK: DİNAMİK PORT AYARI
// process.env.PORT Render'ın bize verdiği porttur. Yoksa yerelde 3000 kullanır.
const PORT = process.env.PORT || 3000;

// 3. DEĞİŞİKLİK: Socket.IO Kurulumu ve CORS Ayarı
// Bu, sunucunuzun farklı adreslerden (client) gelen bağlantılara izin vermesini sağlar.
const io = require('socket.io')(server, {
    cors: {
        origin: "*", // Tüm adreslerden bağlantıya izin ver (güvenlik nedeniyle daha sonra Render URL'nizle kısıtlanabilir)
        methods: ["GET", "POST"]
    }
});


// --- VERİTABANI SIMÜLASYONU VE DURUM YÖNETİMİ (ORİJİNAL KOD) ---
let usersDB = {
    // rw0rR_ YÖNETİCİ HESABI
    'rw0rR_': { 
        username: 'rw0rR_', 
        password: '12345', 
        profilePic: '👑', 
        bio: 'Sistemin Kurucusu', 
        role: 'admin', 
        color: '#000000' 
    }
};
let messages = []; 
let currentUsers = {}; 

let channels = [
    { id: 'genel', name: 'genel-sohbet', type: 'text', category: 'GENEL' },
    { id: 'duyuru', name: 'duyurular', type: 'text', category: 'GENEL' },
    { id: 'giris', name: 'giris-cikis', type: 'text', category: 'SİSTEM' },
    { id: 'destek', name: 'destek-talepleri', type: 'text', category: 'SİSTEM' },
];
let categories = ['GENEL', 'SİSTEM'];
let tickets = [];

function broadcastChannels() {
    io.emit('channel_list_update', channels, categories);
}

function broadcastUsers() {
    const activeUsers = Object.keys(currentUsers).map(id => {
        const userId = currentUsers[id].userId;
        const user = usersDB[userId];
        return {
            socketId: id,
            username: user.username,
            profilePic: user.profilePic,
            bio: user.bio,
            color: user.color,
            isAdmin: user.role === 'admin',
            currentChannelId: currentUsers[id].currentChannelId,
            status: 'online', 
        };
    });
    
    const allUsers = Object.keys(usersDB).map(userId => {
        const user = usersDB[userId];
        const activeSession = activeUsers.find(u => u.username === userId);
        
        return {
            username: user.username,
            profilePic: user.profilePic,
            color: user.color,
            isAdmin: user.role === 'admin',
            role: user.role, 
            status: activeSession ? 'online' : 'offline', 
            currentChannelId: activeSession ? activeSession.currentChannelId : null,
            bio: user.bio,
        };
    });

    io.emit('user_list_update', allUsers);
}

function getMessagesForChannel(channelId) {
    return messages
        .filter(m => m.channel === channelId)
        .map(m => {
            const user = usersDB[m.userId] || { username: 'Bilinmeyen', profilePic: '❓', color: '#72767d' };
            return {
                id: m.id,
                username: user.username,
                profilePic: user.profilePic,
                color: user.color,
                message: m.message,
                time: m.time,
                userId: m.userId,
            };
        });
}

function isAdmin(userId) {
    return usersDB[userId] && usersDB[userId].role === 'admin';
}

// --- EXPRESS AYARLARI ---
app.use(express.static(__dirname));
app.get('/', (req, res) => {
    res.sendFile(__dirname + '/index.html');
});

// --- SOCKET LOGİĞİ ---
io.on('connection', (socket) => {
    let currentUserId = null; 

    // Giriş / Kayıt
    socket.on('auth_request', (data) => {
        if (data.type === 'register') {
            if (usersDB[data.username]) {
                socket.emit('auth_result', { success: false, message: 'Bu kullanıcı adı zaten kayıtlı.' });
                return;
            }
            usersDB[data.username] = {
                username: data.username,
                password: data.password,
                profilePic: data.profilePic || data.username[0].toUpperCase(),
                bio: data.bio || 'Yeni katılan bir kullanıcı.',
                role: 'user',
                color: data.username === 'rw0rR_' ? '#000000' : '#5865F2', 
            };
            socket.emit('auth_result', { success: true, message: 'Kayıt başarılı! Giriş yapabilirsiniz.' });
        } else if (data.type === 'login') {
            const user = usersDB[data.username];
            if (!user || user.password !== data.password) {
                socket.emit('auth_result', { success: false, message: 'Kullanıcı adı veya şifre hatalı.' });
                return;
            }
            
            currentUserId = user.username;
            currentUsers[socket.id] = { 
                userId: currentUserId, 
                currentChannelId: 'genel',
                isAdmin: isAdmin(currentUserId),
                status: 'online'
            };
            
            socket.emit('auth_result', { success: true, user: user });
            socket.emit('initial_messages', getMessagesForChannel('genel'));
            
            const isNewLogin = Object.keys(currentUsers).filter(id => currentUsers[id].userId === currentUserId).length === 1;

            if (isNewLogin) {
                 io.emit('mesaj_al', {isim: 'SİSTEM', message: `${user.username} sunucuya katıldı.`, channel: 'giris'}); 
            }
            
            if(isAdmin(currentUserId)) {
                socket.emit('admin_panel_data', { 
                    users: Object.values(usersDB).map(u => ({ username: u.username, role: u.role, bio: u.bio, profilePic: u.profilePic })), 
                    tickets: tickets 
                });
            }
            
            broadcastChannels();
            broadcastUsers();
        }
    });

    // Sayfa Yenileme veya Tekrar Bağlantı İsteği (F5 Kurtarma)
    socket.on('user_reconnect', (username) => {
        const user = usersDB[username];
        if (!user) return; 
        
        currentUserId = user.username;
        currentUsers[socket.id] = { 
            userId: currentUserId, 
            currentChannelId: 'genel', 
            isAdmin: isAdmin(currentUserId),
            status: 'online'
        };

        socket.emit('reconnect_success', user); 
        socket.emit('initial_messages', getMessagesForChannel('genel'));
        
        if(isAdmin(currentUserId)) {
            socket.emit('admin_panel_data', { 
                users: Object.values(usersDB).map(u => ({ username: u.username, role: u.role, bio: u.bio, profilePic: u.profilePic })), 
                tickets: tickets 
            });
        }
        
        broadcastChannels(); 
        broadcastUsers();
    });
    
    // Mesajlaşma
    socket.on('mesaj_yolla', (data) => {
        if (!currentUserId) return;
        let messageText = data.mesaj;
        let receivers = [data.channel]; 

        // @everyone ve @here işleme
        if (messageText.includes('@everyone')) {
             io.emit('mesaj_al', {isim: 'SİSTEM', message: `@everyone: ${usersDB[currentUserId].username} bir duyuru yaptı.`, channel: data.channel});
        } 
        if (messageText.includes('@here')) {
             io.emit('mesaj_al', {isim: 'SİSTEM', message: `@here: ${usersDB[currentUserId].username} çevrimiçi olanları etiketledi.`, channel: data.channel});
        }

        const msg = {
            id: uuidv4(),
            userId: currentUserId,
            channel: data.channel,
            message: messageText,
            time: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
        };
        messages.push(msg);
        
        io.emit('mesaj_al', {
            id: msg.id,
            username: usersDB[currentUserId].username, 
            profilePic: usersDB[currentUserId].profilePic,
            color: usersDB[currentUserId].color,
            message: messageText, 
            channel: data.channel,
            userId: currentUserId,
            time: msg.time
        });
    });
    
    // Kullanıcı Profili Güncelleme (Admin veya kendi kullanıcısı)
    socket.on('update_user_profile', (data) => {
        if (!currentUserId) return;
        const targetUser = usersDB[data.username];
        
        if (!targetUser) {
            socket.emit('update_result', { success: false, message: 'Kullanıcı bulunamadı.' });
            return;
        }

        if (currentUserId === data.username) {
            targetUser.bio = data.bio || targetUser.bio;
            targetUser.profilePic = data.profilePic || targetUser.profilePic;
            socket.emit('user_self_updated', targetUser); 

        } else if (isAdmin(currentUserId)) {
            targetUser.username = data.newUsername || targetUser.username;
            targetUser.bio = data.bio || targetUser.bio;
            targetUser.profilePic = data.profilePic || targetUser.profilePic;
            targetUser.role = data.role || targetUser.role; 

            if (data.newUsername && data.newUsername !== data.username) {
                usersDB[data.newUsername] = targetUser;
                delete usersDB[data.username];
            }
            
            socket.emit('update_result', { success: true, message: `${data.username} güncellendi.` });

        } else {
            socket.emit('update_result', { success: false, message: 'Yetkisiz işlem.' });
            return;
        }

        broadcastUsers();
    });

    // Admin Panelinden Kullanıcı Silme
    socket.on('admin_delete_user', (username) => {
        if (!isAdmin(currentUserId) || username === 'rw0rR_') {
            socket.emit('update_result', { success: false, message: 'Yetkiniz yok veya ana kullanıcıyı silemezsiniz.' });
            return;
        }
        if (usersDB[username]) {
            delete usersDB[username];
            
            Object.keys(currentUsers).forEach(socketId => {
                if (currentUsers[socketId].userId === username) {
                    io.to(socketId).emit('force_logout');
                    delete currentUsers[socketId];
                }
            });

            socket.emit('update_result', { success: true, message: `${username} başarıyla silindi.` });
            broadcastUsers();
        } else {
            socket.emit('update_result', { success: false, message: 'Kullanıcı bulunamadı.' });
        }
    });

    // Destek Talebi Oluşturma
    socket.on('create_support_ticket', (content) => {
        if (!currentUserId) return;
        
        const newTicket = {
            id: uuidv4(),
            userId: currentUserId,
            username: usersDB[currentUserId].username,
            content: content,
            status: 'Açık',
            time: new Date().toLocaleString('tr-TR'),
        };
        tickets.push(newTicket);
        io.emit('new_ticket_alert', newTicket); 
        socket.emit('update_result', { success: true, message: 'Destek talebiniz başarıyla oluşturuldu.' });
        
        if(isAdmin(currentUserId)) {
             socket.emit('admin_panel_data', { 
                users: Object.values(usersDB).map(u => ({ username: u.username, role: u.role, bio: u.bio, profilePic: u.profilePic })), 
                tickets: tickets 
            });
        }
    });
    
    // Destek Talebi Güncelleme (Admin)
    socket.on('update_support_ticket_status', (ticketId, newStatus) => {
        if (!isAdmin(currentUserId)) return;
        const ticket = tickets.find(t => t.id === ticketId);
        if (ticket) {
            ticket.status = newStatus;
            socket.emit('update_result', { success: true, message: `Talep #${ticketId} güncellendi.` });
            
              io.emit('admin_panel_data', { 
                users: Object.values(usersDB).map(u => ({ username: u.username, role: u.role, bio: u.bio, profilePic: u.profilePic })), 
                tickets: tickets 
            });
        }
    });


    socket.on('delete_message', (messageId) => {
        const messageIndex = messages.findIndex(m => m.id === messageId && (m.userId === currentUserId || isAdmin(currentUserId)));
        
        if (messageIndex !== -1) {
            const channelId = messages[messageIndex].channel;
            messages.splice(messageIndex, 1);
            io.emit('message_deleted', messageId, channelId);
        }
    });
    
    socket.on('get_initial_messages', (channelId) => {
        socket.emit('initial_messages', getMessagesForChannel(channelId));
    });

    socket.on('get_channels', () => {
        socket.emit('channel_list_update', channels, categories);
    });

    socket.on('create_channel', (data) => {
        if (!currentUserId || !isAdmin(currentUserId)) return;
        
        if (data.type === 'category') {
            if (!categories.includes(data.category)) {
                categories.push(data.category);
                broadcastChannels();
            }
        } else {
            const newChannelId = data.name;
            if (!channels.some(c => c.id === newChannelId)) {
                channels.push({ 
                    id: newChannelId, 
                    name: data.name, 
                    type: 'text',
                    category: (data.category || 'GENEL').toUpperCase() 
                });
                broadcastChannels();
            }
        }
    });

    socket.on('delete_channel', (channelId) => {
        if (!currentUserId || !isAdmin(currentUserId) || channelId === 'genel' || channelId === 'duyuru' || channelId === 'giris' || channelId === 'destek') return;

        channels = channels.filter(c => c.id !== channelId);
        
        const categoryToRemove = channels.find(c => c.category === channels.find(c => c.id === channelId)?.category)?.category;
        if (!categoryToRemove) {
             categories = categories.filter(cat => cat !== channels.find(c => c.id === channelId)?.category);
        }

        broadcastChannels();
        io.emit('channel_deleted_info', channelId); 
    });


    // Bağlantı kesildiğinde 
    socket.on('disconnect', () => {
        if (currentUserId && currentUsers[socket.id]) {
            delete currentUsers[socket.id];
            
            const remainingConnections = Object.keys(currentUsers).filter(id => currentUsers[id].userId === currentUserId);

            if (remainingConnections.length === 0) {
                io.emit('mesaj_al', {isim: 'SİSTEM', message: `${usersDB[currentUserId].username} sunucudan ayrıldı.`, channel: 'giris'});
            }
            
            broadcastUsers(); 
        }
    });
});

// 4. SON DEĞİŞİKLİK: Sunucuyu dinlemeye alma. 'server' objesini ve 'PORT' değişkenini kullanır.
server.listen(PORT, () => {
  console.log(`Sunucu ${PORT} portunda çalışıyor. LAWIANDREW CHAT Aktif!`);
});