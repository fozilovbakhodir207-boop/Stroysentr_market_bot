const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const userId = tg.initDataUnsafe?.user?.id || 0;
const ADMIN_ID = 6986848905; 

// Adminlikni tekshirish
if (String(userId) === String(ADMIN_ID)) {
    const adminPanel = document.getElementById("admin-panel");
    if (adminPanel) adminPanel.style.display = "block";
}

// Mahsulotlarni serverdan yuklab olish
async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        const data = await response.json();
        
        const listDiv = document.getElementById('products-list');
        listDiv.innerHTML = '';

        if (data.products && data.products.length > 0) {
            data.products.forEach(p => {
                const imgSrc = p.image_url ? p.image_url : 'https://via.placeholder.com/150';
                listDiv.innerHTML += `
                    <div class="product-card">
                        <img src="${imgSrc}" alt="${p.title}">
                        <h4>${p.title}</h4>
                        <div class="price">${Number(p.price).toLocaleString()} so'm</div>
                        <button onclick="buyProduct('${p.title}', ${p.price})">Sotib olish</button>
                    </div>
                `;
            });
        } else {
            listDiv.innerHTML = '<p>Hozircha mahsulotlar yo\'q.</p>';
        }
    } catch (err) {
        console.error(err);
        document.getElementById('products-list').innerHTML = '<p>Xatolik yuz berdi.</p>';
    }
}

// Admin uchun: Mahsulot qo'shish
async function addProduct() {
    const title = document.getElementById('prod-title').value;
    const price = document.getElementById('prod-price').value;
    const stock = document.getElementById('prod-stock').value;
    const imageFile = document.getElementById('prod-image').files[0];
    const statusText = document.getElementById('admin-status');

    if (!title || !price) {
        alert("Nom va narxni kiriting!");
        return;
    }

    statusText.innerText = "Yuklanmoqda...";

    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('title', title);
    formData.append('price', price);
    formData.append('stock', stock || 0);
    if (imageFile) {
        formData.append('image', imageFile);
    }

    try {
        const res = await fetch('/api/products/add', {
            method: 'POST',
            body: formData
        });
        const result = await res.json();

        if (result.status === 'success') {
            statusText.innerText = "✅ Qo'shildi!";
            document.getElementById('prod-title').value = '';
            document.getElementById('prod-price').value = '';
            document.getElementById('prod-stock').value = '';
            document.getElementById('prod-image').value = '';
            loadProducts();
        } else {
            statusText.innerText = "❌ Xatolik: " + result.message;
        }
    } catch (e) {
        statusText.innerText = "❌ Server bilan aloqa yo'q.";
    }
}

// Buyurtma berish
async function buyProduct(title, price) {
    const userName = tg.initDataUnsafe?.user?.first_name || 'Xaridor';
    
    if (confirm(`${title} mahsulotini buyurtma qilasizmi?`)) {
        try {
            const res = await fetch('/api/orders/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_name: userName,
                    phone: 'Telegram orqali',
                    address: 'Telegram Mini App',
                    items: [{ title: title, quantity: 1, price: price }],
                    total_price: price
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                alert(" Buyurtmangiz qabul qilindi! Guruhga yuborildi.");
            }
        } catch (e) {
            alert("Xatolik yuz berdi.");
        }
    }
}

// Sahifa yuklanganda ishga tushirish
loadProducts();
