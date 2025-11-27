/* LAWIANDREW CHAT - client.js (SESLİ KANALSIZ NIHAI VE KARARLI KOD) */

var socket = io();
let myUser = null; 
let currentChannelId = 'genel'; 
let currentChannelType = 'text'; // Sadece 'text' kalacak
let channelList = []; 
let userList = [];
let isAuthMode = 'login'; 
let contextMenuTargetId = null;
let contextMenuTargetName = null;

// --- BAŞLANGIÇ VE GİRİŞ/KAYIT ---

function updateUserInfoPanel(user) {
    document.getElementById('my-profile-icon').style.background = user.color || '#5865F2';
    document.getElementById('my-profile-icon').innerText = user.profilePic || user.username[0].toUpperCase();
    document.getElementById('my-username').innerText = user.username;
}

function logout() {
    localStorage.removeItem('chat_user');
    myUser = null;
    window.location.reload(); 
}

window.onload = function() {
    setupEventListeners();
    const storedUser = localStorage.getItem('chat_user');
    
    if (storedUser) {
        myUser = JSON.parse(storedUser);
        document.getElementById('login').style.display = 'none';
        
        socket.emit('user_reconnect', myUser.username); 
        
        updateUserInfoPanel(myUser); 
        socket.emit('get_channels');
    }
}

socket.on('reconnect_success', (user) => {
    myUser = {
        username: user.username,
        profilePic: user.profilePic,
        bio: user.bio,
        color: user.color,
        isAdmin: user.role === 'admin'
    };
    
    document.getElementById('login').style.display = 'none';
    updateUserInfoPanel(myUser); 
    
    socket.emit('get_channels');
    selectChannel('genel', 'genel-sohbet', 'text', true); 
});


function setupEventListeners() {
    document.getElementById('msg-input').addEventListener('keypress', function (e) {
        if (e.key === 'Enter' && myUser) {
            sendMessage();
        }
    });

    // Sağ tık menüsü
    document.addEventListener('contextmenu', (e) => {
        // Kanal Listesine sağ tıklama
        if (e.target.closest('#channel-list-container')) {
            e.preventDefault();
            const menu = document.getElementById('context-menu');
            
            // Yöneticilik kontrolü
            if (myUser && myUser.isAdmin) {
                 document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
            } else {
                 document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
            }
            
            // Sadece Text kanalı oluşturma görünecek, Sesli ayrılma butonu kaldırıldı
            menu.style.top = `${e.clientY}px`;
            menu.style.left = `${e.clientX}px`;
            menu.style.display = 'block';

        } else {
            document.getElementById('context-menu').style.display = 'none';
        }
    });
    
    document.addEventListener('click', () => {
        document.getElementById('context-menu').style.display = 'none';
    });
}

function switchAuthMode() {
    // ... (Giriş/Kayıt mantığı aynı) ...
    const title = document.getElementById('auth-title');
    const switchBtn = document.getElementById('switch-auth');
    const registerFields = document.getElementById('register-fields');
    const authBtn = document.querySelector('.login-box button');
    
    if (isAuthMode === 'login') {
        isAuthMode = 'register';
        title.innerText = 'Kayıt Ol 📝';
        switchBtn.innerText = 'Zaten hesabın var mı? Giriş Yap';
        registerFields.style.display = 'block';
        authBtn.innerText = 'Kayıt Ol';
    } else {
        isAuthMode = 'login';
        title.innerText = 'Giriş Yap 🔑';
        switchBtn.innerText = 'Hesabın yok mu? Kayıt Ol';
        registerFields.style.display = 'none';
        authBtn.innerText = 'Giriş Yap';
    }
    document.getElementById('auth-error').innerText = '';
    document.getElementById('auth-success').innerText = '';
}

function handleAuth() {
    // ... (Auth mantığı aynı) ...
    const username = document.getElementById('auth-username').value.trim();
    const password = document.getElementById('auth-password').value.trim();
    const profilePic = document.getElementById('auth-profile-pic').value.trim();
    const bio = document.getElementById('auth-bio').value.trim();

    if (username.length < 3 || password.length < 4) {
        showAuthMessage('Hata', 'Kullanıcı adı/şifre kısa.', false);
        return;
    }
    
    socket.emit('auth_request', {
        type: isAuthMode,
        username: username,
        password: password,
        profilePic: profilePic || username[0].toUpperCase(),
        bio: bio
    });
}

socket.on('auth_result', (result) => {
    // ... (Auth sonucu mantığı aynı) ...
    if (result.success) {
        if (isAuthMode === 'register') {
            showAuthMessage('Başarılı', result.message, true);
            switchAuthMode(); 
        } else {
            myUser = {
                username: result.user.username,
                profilePic: result.user.profilePic,
                bio: result.user.bio,
                color: result.user.color,
                isAdmin: result.user.role === 'admin'
            };
            localStorage.setItem('chat_user', JSON.stringify(myUser));
            document.getElementById('login').style.display = 'none';
            updateUserInfoPanel(myUser); 
            socket.emit('get_channels');
            selectChannel('genel', 'genel-sohbet', 'text');
        }
    } else {
        showAuthMessage('Hata', result.message, false);
    }
});

function showAuthMessage(type, message, isSuccess) {
    const errorEl = document.getElementById('auth-error');
    const successEl = document.getElementById('auth-success');
    
    errorEl.innerText = isSuccess ? '' : message;
    successEl.innerText = isSuccess ? message : '';
}

socket.on('initial_messages', (initialMessages) => {
    // ... (Mesaj yükleme mantığı aynı) ...
    document.getElementById('message-container').innerHTML = '';
    initialMessages.forEach(msg => {
        appendMessage(msg.username, msg.message, msg.id, msg.userId, msg.time, msg.profilePic, msg.color);
    });
    
    const container = document.getElementById('message-container');
    container.scrollTop = container.scrollHeight;
    
    if(channelList.length > 0) {
        const currentChannel = channelList.find(c => c.id === currentChannelId);
        if(currentChannel) {
            selectChannel(currentChannel.id, currentChannel.name, currentChannel.type, false); 
        } else {
            selectChannel('genel', 'genel-sohbet', 'text', false);
        }
    }
});

// --- MESAJLAR VE SİLME ---

function sendMessage() {
    // ... (Mesaj gönderme mantığı aynı) ...
    const inputField = document.getElementById('msg-input');
    var txt = inputField.value;
    if(txt.trim() !== "" && myUser) { 
        socket.emit('mesaj_yolla', {isim: myUser.username, mesaj: txt, channel: currentChannelId}); 
        inputField.value = '';
    }
}

socket.on('mesaj_al', function(data) {
    // ... (Mesaj alma mantığı aynı) ...
    if(data.channel === currentChannelId || data.channel === 'giris' || data.isim === 'SİSTEM') {
        appendMessage(data.username || data.isim, data.message, data.id, data.userId, data.time, data.profilePic, data.color); 
    }
});

socket.on('message_deleted', (messageId, channelId) => {
    // ... (Mesaj silme mantığı aynı) ...
    if (channelId === currentChannelId) {
        const msgEl = document.getElementById('msg-' + messageId);
        if (msgEl) {
            const msgContent = msgEl.querySelector('.msg-content p');
            if (msgContent) {
                 msgContent.innerHTML = '<i style="color:#faa61a;">[mesaj Yönetici veya Kullanıcı tarafından kaldırılmıştır]</i>';
            }
            msgEl.querySelector('.delete-message-btn')?.remove();
        }
    }
});

function deleteMessage(messageId) {
    // ... (Mesaj silme onayı aynı) ...
    if (myUser && confirm('Bu mesajı silmek istediğinizden emin misiniz?')) {
        socket.emit('delete_message', messageId);
    }
}

function appendMessage(user, text, id, userId, time, profilePic, color) { 
    // ... (Mesaj ekleme mantığı aynı) ...
    var container = document.getElementById('message-container');
    const isSystem = user === 'SİSTEM';
    const isOwn = myUser && userId === myUser.username;
    
    const avatarColor = color || '#FAA61A';
    const avatarContent = profilePic || user[0].toUpperCase();
    
    var html = `
    <div class="msg" id="msg-${id}">
        <div class="avatar" style="background: ${isSystem ? '#72767d' : avatarColor}; color: white;" onclick="openProfileModal('${userId}')">${isSystem ? '🤖' : avatarContent}</div>
        <div class="msg-content">
            <h4><span style="color: ${isSystem ? '#F2C744' : avatarColor};" onclick="openProfileModal('${userId}')">${user}</span> <span>${time}</span></h4>
            <p>${text}</p>
            ${(isOwn && id) || (myUser && myUser.isAdmin && id) ? `<button class="delete-message-btn own-message" onclick="deleteMessage('${id}')" title="Mesajı Sil"><i class="fas fa-times"></i></button>` : ''}
        </div>
    </div>`;
    
    container.innerHTML += html;
    container.scrollTop = container.scrollHeight;
}

// --- EMOJİ VE PROFİL ---

function toggleEmojiPicker() {
    const picker = document.getElementById('emoji-picker');
    picker.style.display = picker.style.display === 'none' ? 'block' : 'none';
}

function insertEmoji(emoji) {
    const input = document.getElementById('msg-input');
    input.value += emoji;
    toggleEmojiPicker();
    input.focus();
}

function openProfileModal(userId) {
    // ... (Profil modalı açma mantığı aynı) ...
    const user = userList.find(u => u.username === userId) || (myUser && myUser.username === userId ? myUser : null);

    if (!user) return;
    
    document.getElementById('modal-avatar').style.background = user.color || '#5865F2';
    document.getElementById('modal-avatar').innerText = user.profilePic || user.username[0].toUpperCase();
    document.getElementById('modal-name').innerText = user.username + (user.isAdmin ? ' 👑' : '');
    document.getElementById('modal-bio').innerText = user.bio || 'Biyografi Yok.';
    document.getElementById('profile-modal').style.display = 'flex';
}

function closeProfileModal() {
    document.getElementById('profile-modal').style.display = 'none';
}

// --- KANAL VE KULLANICI LİSTESİ ---

function toggleChannels() {
    // ... (Mobil menü mantığı aynı) ...
    document.getElementById('channels-wrapper').classList.toggle('active');
    if (window.innerWidth <= 768) {
        if (document.getElementById('user-list-wrapper').classList.contains('active')) {
            document.getElementById('user-list-wrapper').classList.remove('active');
        }
    }
}

function toggleUserList() {
    // ... (Mobil menü mantığı aynı) ...
    document.getElementById('user-list-wrapper').classList.toggle('active');
    if (window.innerWidth <= 768) {
        if (document.getElementById('channels-wrapper').classList.contains('active')) {
            document.getElementById('channels-wrapper').classList.remove('active');
        }
    }
}

function selectChannel(id, name, type, requestMessages = true) {
    if (!myUser) return;
    
    currentChannelId = id;
    currentChannelType = 'text'; // Her zaman text olarak ayarlandı
    
    document.getElementById('current-channel-name').innerText = name;

    if (requestMessages) {
        socket.emit('get_initial_messages', currentChannelId);
    }
    
    const inputArea = document.querySelector('.input-area');
    const channelIcon = document.getElementById('channel-type-icon');
    
    if (window.innerWidth <= 768) {
         document.getElementById('channels-wrapper').classList.remove('active');
         document.getElementById('user-list-wrapper').classList.remove('active');
    }
    
    inputArea.style.display = 'block'; 
    document.getElementById('msg-input').placeholder = `#${name} kanalına mesaj gönder...`;

    channelIcon.className = 'fas fa-hashtag'; // Sadece hashtag ikonu
    
    document.querySelectorAll('.channel-item').forEach(el => el.classList.remove('active'));
    const selectedChannelEl = document.getElementById('channel-' + id);
    if (selectedChannelEl) {
        selectedChannelEl.classList.add('active');
    }
}

socket.on('channel_list_update', function(updatedChannels, updatedCategories) {
    channelList = updatedChannels;
    const container = document.getElementById('channel-list-container');
    container.innerHTML = '';
    
    updatedCategories.forEach(category => {
        container.innerHTML += `
            <div class="channel-group-title" onclick="toggleCategory('${category}')">
                ${category} <i class="fas fa-chevron-down"></i>
            </div>
            <div id="category-${category}" class="channel-group-content">
            </div>
        `;
        
        const categoryContent = document.getElementById(`category-${category}`);
        updatedChannels.filter(c => c.category === category).forEach(channel => {
            const isActive = channel.id === currentChannelId ? ' active' : '';
            const isProtected = channel.id === 'genel' || channel.id === 'duyuru' || channel.id === 'giris';
            
            // Sesli kanal ikonu yok, sadece hashtag var
            categoryContent.innerHTML += `
                <div class="channel-item${isActive}" id="channel-${channel.id}" onclick="selectChannel('${channel.id}', '${channel.name}', 'text')">
                    <div class="channel-item-name">
                        <span><i class="fas fa-hashtag"></i></span> ${channel.name}
                    </div>
                    ${myUser && myUser.isAdmin && !isProtected ? `
                        <div class="channel-actions">
                             <button onclick="event.stopPropagation(); deleteChannel('${channel.id}', '${channel.name}')" title="Sil"><i class="fas fa-trash"></i></button>
                        </div>
                    ` : ''}
                </div>`;
        });
    });
    if (currentChannelId) {
        const current = channelList.find(c => c.id === currentChannelId);
        if (current) selectChannel(current.id, current.name, current.type, false);
    }
});

function toggleCategory(category) {
    // ... (Kategori kapatma/açma mantığı aynı) ...
    const categoryEl = document.getElementById(`category-${category}`);
    const icon = categoryEl.previousElementSibling.querySelector('i');
    if (categoryEl.style.display === 'none') {
        categoryEl.style.display = 'block';
        icon.className = 'fas fa-chevron-down';
    } else {
        categoryEl.style.display = 'none';
        icon.className = 'fas fa-chevron-right';
    }
}


socket.on('user_list_update', function(updatedUsers) {
    // ... (Kullanıcı listesi mantığı basitleştirildi) ...
    userList = updatedUsers;
    const container = document.getElementById('users-in-channel');
    container.innerHTML = '';
    
    // Tüm kullanıcılar text kanallarda gibi gösterilir
    const usersToShow = updatedUsers;
        
    const onlineUsers = usersToShow.filter(u => u.status === 'online');
    const offlineUsers = usersToShow.filter(u => u.status === 'offline');
    
    if (usersToShow.length === 0) {
        container.innerHTML = '<h4>SUNUCUDA KULLANICI YOK</h4>';
    }
    
    if (onlineUsers.length > 0) {
        container.innerHTML += `<h4>ÇEVRİMİÇİ (${onlineUsers.length})</h4>`;
        onlineUsers.forEach(user => {
            container.innerHTML += createUserListItem(user);
        });
    }

    if (offlineUsers.length > 0) {
        container.innerHTML += `<h4>ÇEVRİMDIŞI (${offlineUsers.length})</h4>`;
        offlineUsers.forEach(user => {
             container.innerHTML += createUserListItem(user);
        });
    }
});

function createUserListItem(user) {
    const isAdmin = user.isAdmin ? ' admin' : '';
    const statusClass = user.status === 'online' ? 'status-online' : 'status-offline';
    
    return `
        <div class="user-item" onclick="openProfileModal('${user.username}')">
            <div class="user-icon${isAdmin}" style="background: ${user.color || '#5865F2'};">${user.profilePic}
                <div class="status-dot ${statusClass}"></div>
            </div>
            <div class="user-name${isAdmin}">${user.username}</div>
        </div>`;
}

// --- KANAL YÖNETİMİ EK İŞLEMLERİ ---

function promptChannelName(type) {
    if (!myUser || !myUser.isAdmin) return alert('Bu işlem için yönetici yetkisi gereklidir.');

    let promptText;
    let newType = type;
    let category = '';
    
    if (type === 'category') {
        promptText = "Yeni kategori adını girin (Örn: OYUNLAR):";
    } else {
        promptText = "Yeni yazı kanalının adını girin (Örn: sohbet-2):";
        const categoriesList = channelList.map(c => c.category).filter((value, index, self) => self.indexOf(value) === index && value && value !== 'undefined');
        category = prompt(`Hangi kategoriye eklensin? (Mevcutlar: ${categoriesList.join(', ') || 'Yok - Boş bırakırsanız GENEL olur'})`);
        if (category === null) return;
    }
    
    let name = prompt(promptText);
    if (name && name.trim() !== "") {
        name = name.trim().toLowerCase().replace(/\s+/g, '-').slice(0, 20); 
        socket.emit('create_channel', { 
            name: name, 
            type: newType, // server tarafında her zaman 'text' olarak ayarlanacak
            category: (category || 'GENEL').toUpperCase() 
        });
    }
}

function deleteChannel(id, name) {
     if (!myUser || !myUser.isAdmin) return alert('Bu işlem için yönetici yetkisi gereklidir.');

     if (confirm(`'${name}' kanalını silmek istediğinden emin misin?`)) {
         socket.emit('delete_channel', id);
     }
}

socket.on('channel_deleted_info', (deletedChannelId) => {
    if (deletedChannelId === currentChannelId) {
        // Silinen kanalda isek, genel kanala geç
        const generalChannel = channelList.find(c => c.id === 'genel');
        if (generalChannel) {
            selectChannel(generalChannel.id, generalChannel.name, generalChannel.type, true);
        }
    }
});