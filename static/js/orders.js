document.addEventListener("DOMContentLoaded", function () {
    const orderCards = document.querySelectorAll('.table-card');

    let lastCheckedBox = null;

    function updateInputs(checkbox) {
        const card = checkbox.closest('.table-card');
        
        const id = card.querySelector('.order-id').textContent.trim();
        const restaurantID = card.querySelector('.order-restaurant-id').textContent.trim();
        const fullDateText = card.querySelector('.order-date').textContent.trim();  
        const dateOnly = fullDateText.split(' ')[0];
        const orderStatus = card.querySelector('.order-status').textContent.trim();
        const salesQty = card.querySelector('.order-sales-quantity').textContent.trim(); 
        const salesAmount = card.querySelector('.order-sales-amount').textContent.replace('$', '').trim();
        const tableNo = card.querySelector('.order-table-no')?.textContent.trim() || '';
        const type = card.querySelector('.order-type')?.textContent.trim() || 'Dine-in';
        const cName = card.querySelector('.customer-name')?.textContent.trim() || '';
        const cPhone = card.querySelector('.customer-phone')?.textContent.trim() || '';
        const cAddress = card.querySelector('.customer-address')?.textContent.trim() || '';
        const courierId = card.querySelector('.courier-id')?.textContent.trim() || '';      

        const adminRestInput = document.getElementById('add-order-restaurant-id'); 
        const userRestInput = document.getElementById('order-restaurant-id');     

        // Arkadaki gizli ID'leri güvenle doldur
        if (adminRestInput) adminRestInput.value = restaurantID;
        if (userRestInput) userRestInput.value = restaurantID;

        // Sayfa yüklendiğinde kuryeler zaten var olduğu için beklemeden ANINDA seç!
        const courierSelect = document.getElementById('dynamic-courier-list');
        if (courierSelect) {
            courierSelect.value = courierId;
        }

        document.getElementById('order-id').value = id;
        document.getElementById('order-date').value = dateOnly;
        document.getElementById('order-status').value = orderStatus;
        document.getElementById('order-sales-quantity').value = salesQty; 
        document.getElementById('order-sales-amount').value = salesAmount; 
        document.getElementById('update-order-id').value = id;
        document.getElementById('order-type').value = type;
        
        const tableNoInput = document.getElementById('order-table-no');
        if (tableNoInput) tableNoInput.value = tableNo;

        if(document.getElementById('customer-name')) document.getElementById('customer-name').value = cName;
        if(document.getElementById('customer-phone')) document.getElementById('customer-phone').value = cPhone;
        if(document.getElementById('customer-address')) document.getElementById('customer-address').value = cAddress;
        
        toggleOrderFields(); 

        const foodContainer = document.getElementById('food-items-container');

        if (type === 'Delivery' && id) {
            
            const firstSelect = document.querySelector('select[name="food_id"]');
            const optionsHTML = firstSelect ? firstSelect.innerHTML : '<option value="">Select Food...</option>';

            document.body.style.cursor = "wait"; 

            fetch(`/order_details/${id}`)
                .then(response => response.json())
                .then(data => {
                    foodContainer.innerHTML = ''; 

                    if (data.length > 0) {
                        
                        let allRowsHTML = ''; 

                        data.forEach((item, index) => {
                            const removeBtn = index === 0 ? '' : 
                                `<button type="button" class="remove-btn" onclick="this.parentElement.remove()" 
                                style="background: #dc3545; color: white; border: none; padding: 0 8px; cursor: pointer; margin-left: 5px;">X</button>`;

                            
                            allRowsHTML += `
                                <div class="food-row" style="display: flex; gap: 5px; margin-bottom: 5px; width: 100%;">
                                    <select name="food_id" class="food-select dynamic-food-list" style="flex: 2; height: 35px; padding: 5px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px;">
                                        ${optionsHTML} 
                                    </select>
                                    <input type="number" name="quantity" value="${item.quantity}" min="1" 
                                           style="flex: 0.8; height: 35px; padding: 5px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px;">
                                    ${removeBtn}
                                </div>
                            `;
                        });

                        foodContainer.innerHTML = allRowsHTML;

                        // Zaman kaybetmeden yemekleri anında seç
                        const selectBoxes = foodContainer.querySelectorAll('.food-select');
                        selectBoxes.forEach((box, index) => {
                            if (data[index] && box) {
                                box.value = data[index].food_id;
                            }
                        });

                    } else {
                        addFoodRow(); 
                    }
                })
                .catch(err => console.error(err))
                .finally(() => {
                    document.body.style.cursor = "default";
                });
        }
        
        const role = document.getElementById('current-user-role').value;
        const qtyInput = document.getElementById('order-sales-quantity');
        const amtInput = document.getElementById('order-sales-amount');
        const tableInput = document.getElementById('order-table-no');
        const typeSelect = document.getElementById('order-type');
        const idInput = document.getElementById('order-id');
        const resInput = document.getElementById('order-restaurant-id');
        const adminResInputLock = document.getElementById('add-order-restaurant-id'); 

        const inputsToLock = [qtyInput, amtInput, tableInput, typeSelect, idInput, resInput];

        if (role !== 'admin') {
            inputsToLock.forEach(el => {
                if (el) {
                    el.style.backgroundColor = "#e9ecef"; 
                    el.style.cursor = "not-allowed"; 
                    if (el.tagName === 'SELECT') {
                        el.style.pointerEvents = "none"; 
                        el.style.color = "#6c757d"; 
                        el.parentElement.style.cursor = "not-allowed";
                    } else {                  
                        el.readOnly = true; 
                    }
                }
            });
        } else {
            inputsToLock.forEach(el => {
                if (el) {
                    el.style.backgroundColor = ""; 
                    el.style.cursor = ""; 
                    if (el.tagName === 'SELECT') {
                        el.style.pointerEvents = "auto"; 
                        el.style.color = ""; 
                        el.parentElement.style.cursor = "";
                    } else {                  
                        el.readOnly = false; 
                    }
                }
            });
        }

        if (card) {
            card.scrollIntoView({ behavior: 'auto', block: 'nearest' });
        }
    }

    function clearInputs() {
        document.getElementById('order-id').value = '';
        document.getElementById('order-date').value = '';
        document.getElementById('order-status').value = '';
        document.getElementById('order-sales-quantity').value = '';
        document.getElementById('order-sales-amount').value = '';
        document.getElementById('update-order-id').value = '';
        
        const tableInput = document.getElementById('order-table-no');
        if (tableInput) tableInput.value = '';

        const adminRestInput = document.getElementById('add-order-restaurant-id');
        const userRestInput = document.getElementById('order-restaurant-id');

        if (adminRestInput) adminRestInput.value = ''; 
        if (userRestInput) userRestInput.value = '';

        if(document.getElementById('customer-name')) document.getElementById('customer-name').value = '';
        if(document.getElementById('customer-phone')) document.getElementById('customer-phone').value = '';
        if(document.getElementById('customer-address')) document.getElementById('customer-address').value = '';

        // 🚀 ÇÖZÜM 1: Kurye listesini YOK ETME, sadece seçimi sıfırla!
        const courierSelect = document.getElementById('dynamic-courier-list');
        if (courierSelect) {
            courierSelect.value = ''; 
        }

        // 🚀 ÇÖZÜM 2: Yemek listesini SİLME, sadece ilk satırı koruyup değerini sıfırla!
        const foodContainer = document.getElementById('food-items-container');
        if (foodContainer) {
            const rows = foodContainer.querySelectorAll('.food-row');
            if (rows.length > 0) {
                const firstRow = rows[0];
                
                // Sadece ilk satırın değerlerini boşalt
                const selectBox = firstRow.querySelector('select');
                const qtyBox = firstRow.querySelector('input[name="quantity"]');
                if (selectBox) selectBox.value = '';
                if (qtyBox) qtyBox.value = '1';
                
                // Yanındaki kırmızı 'X' silme butonunu kaldır
                const removeBtn = firstRow.querySelector('.remove-btn');
                if (removeBtn) removeBtn.remove();

                // Eğer 2., 3., 4. yemek satırları varsa sadece onları temizle
                for (let i = 1; i < rows.length; i++) {
                    rows[i].remove();
                }
            }
        }
    
        const qtyInput = document.getElementById('order-sales-quantity');
        const amtInput = document.getElementById('order-sales-amount');
        const typeSelect = document.getElementById('order-type');
        const idInput = document.getElementById('order-id');

        const inputsToUnlock = [qtyInput, amtInput, tableInput, typeSelect, idInput, userRestInput];

        inputsToUnlock.forEach(el => {
            if (el) {
                el.style.backgroundColor = ""; 
                el.style.cursor = ""; 
                if (el.tagName === 'SELECT') {
                    el.style.pointerEvents = "auto"; 
                    el.style.color = ""; 
                    el.parentElement.style.cursor = "";
                } else {                  
                    el.readOnly = false; 
                }
            }
        });

        if (typeof toggleOrderFields === 'function') {
            toggleOrderFields(); 
        }
    }

    function handleCheckboxChange(event) {
        const currentCheckbox = event.target;

        // 1. DURUM: Kullanıcı tiki kaldırdıysa
        if (!currentCheckbox.checked) {
            clearInputs(); // Sadece formu temizle, işlemi bitir
            return; 
        }

        // 2. DURUM: Kullanıcı bir siparişe tik attıysa (Tekli Seçim Mantığı)
        // A) Ekranda başka seçili siparişler varsa onların tikini zorla kaldır
        document.querySelectorAll('#order-list input[type="checkbox"]').forEach(cb => {
            if (cb !== currentCheckbox) cb.checked = false;
        });

        // B) Temiz bir sayfayla, sadece tıkladığı bu siparişin bilgilerini yukarı doldur
        updateInputs(currentCheckbox);
    }

    orderCards.forEach(card => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', handleCheckboxChange);
    });
});

let matchedCards = [];
let currentMatchIndex = 0;

function searchOrder() {
    const idInput = document.getElementById('order-id').value.trim();
    const restaurantIDInput = document.getElementById('order-restaurant-id').value.trim();
    const orderDateInput = document.getElementById('order-date').value.trim();
    const orderStatusInput = document.getElementById('order-status').value.trim();
    const salesQtyInput = document.getElementById('order-sales-quantity').value.trim();
    const salesAmountInput = document.getElementById('order-sales-amount').value.trim();
    const tableNoInput = document.getElementById('order-table-no').value.trim();
    
    const cards = document.querySelectorAll('.table-card');
    matchedCards = [];
    currentMatchIndex = -1;

    if (!idInput && !restaurantIDInput && !orderDateInput && 
        !orderStatusInput && !salesQtyInput && !salesAmountInput && !tableNoInput) {
        alert("Please enter at least one search criterion.");
        return;
    }

    cards.forEach(card => card.classList.remove('highlight'));

    cards.forEach(card => {
        const id = card.querySelector('.order-id').textContent.trim();
        const restaurantID = card.querySelector('.order-restaurant-id').textContent.trim();
        const orderDateText = card.querySelector('.order-date').textContent.trim();
        const orderStatus = card.querySelector('.order-status').textContent.trim();
        const salesQty = card.querySelector('.order-sales-quantity').textContent.trim();
        const salesAmount = card.querySelector('.order-sales-amount').textContent.trim();
        const tableNo = card.querySelector('.order-table-no')?.textContent.trim() || '';

        if (
            (!idInput || id === idInput) &&
            (!restaurantIDInput || restaurantID === restaurantIDInput) &&
            (!orderDateInput || orderDateText.includes(orderDateInput)) &&
            (!orderStatusInput || orderStatus.toLowerCase() === orderStatusInput.toLowerCase()) &&
            (!salesQtyInput || salesQty === salesQtyInput) &&
            (!salesAmountInput || salesAmount === salesAmountInput) &&
            (!tableNoInput || tableNo === tableNoInput)
        ) {
            matchedCards.push(card);
        }
    });

    if (matchedCards.length > 0) {
        if (matchedCards.length === 1) {
            document.getElementById('navigation').classList.add('hidden');
        } else {
            document.getElementById('navigation').classList.remove('hidden');
        }
        goToNextMatch();
    } else {
        document.getElementById('navigation').classList.add('hidden');
        alert("No orders found matching the criteria.");
    }
}

function goToNextMatch() {
    if (currentMatchIndex >= 0 && currentMatchIndex < matchedCards.length) {
        matchedCards[currentMatchIndex].classList.remove('highlight');
    }

    currentMatchIndex = (currentMatchIndex + 1) % matchedCards.length;
    const nextCard = matchedCards[currentMatchIndex];

    nextCard.classList.add('highlight');
    nextCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function clearSearch() {
    document.getElementById('order-id').value = "";
    document.getElementById('order-restaurant-id').value = "";
    document.getElementById('order-date').value = "";
    document.getElementById('order-status').value = "";
    document.getElementById('sales-qty').value = "";
    document.getElementById('sales-amount').value = "";

    document.getElementById('clear-filter').value = "true";
    document.getElementById('order-form').submit();

    document.querySelectorAll('.table-card').forEach(card => card.classList.remove('highlight'));
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => checkbox.checked = false);

    matchedCards = [];
    currentMatchIndex = 0;

    document.getElementById('navigation').classList.add('hidden');
}

function collectSelected() {
    const selectedOrders = [];
    const checkboxes = document.querySelectorAll('#order-list input[type="checkbox"]:checked');

    checkboxes.forEach(checkbox => {
        selectedOrders.push(checkbox.value);
    });

    document.getElementById('selected-orders').value = selectedOrders.join(',');
}

const scrollTopBtn = document.getElementById("scrollTopBtn");

function checkScrollPosition() {
    if (window.scrollY > 100) {
        scrollTopBtn.classList.add("visible");
    } else {
        scrollTopBtn.classList.remove("visible");
    }
}

window.addEventListener("load", checkScrollPosition);

window.addEventListener("scroll", checkScrollPosition);

scrollTopBtn.addEventListener("click", function() {
    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
});

function toggleSortMenu(event) {
    const sortMenu = document.getElementById('sort-menu');
    const overlay = document.getElementById('overlay');
    const isHidden = sortMenu.style.display === 'none' || !sortMenu.style.display;

    if (isHidden) {
        sortMenu.style.display = 'block';
        overlay.style.display = 'block';

        const buttonRect = event.target.getBoundingClientRect();
        sortMenu.style.top = `${buttonRect.top + window.scrollY}px`;
        sortMenu.style.left = `${buttonRect.right + 10}px`;
    } else {
        sortMenu.style.display = 'none';
        overlay.style.display = 'none';
    }
}

document.getElementById('overlay').addEventListener('click', function () {
    document.getElementById('sort-menu').style.display = 'none';
    document.getElementById('overlay').style.display = 'none';
});

document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelectorAll(".flash-message");
    flashMessages.forEach((msg) => {
        setTimeout(() => {
            msg.style.display = "none";
        }, 5000);
    });
    toggleOrderFields();
    const restaurantInput = document.getElementById('add-order-restaurant-id');
    const courierSelect = document.getElementById('dynamic-courier-list');
    
    const foodSelects = document.querySelectorAll('.dynamic-food-list'); 

    if (restaurantInput) {
        restaurantInput.addEventListener('change', function () {
            const restaurantId = this.value;

            if (!restaurantId) return;

            fetch(`/get_restaurant_details/${restaurantId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error("Error:", data.error);
                        return;
                    }

                    if (courierSelect) {
                        courierSelect.innerHTML = '<option value="">Select Courier...</option>';
                        if (data.couriers.length > 0) {
                            data.couriers.forEach(courier => {
                                const option = document.createElement('option');
                                option.value = courier.courier_id;
                                option.textContent = `${courier.name} (ID: ${courier.courier_id})`;
                                courierSelect.appendChild(option);
                            });
                        } else {
                            const option = document.createElement('option');
                            option.textContent = "No couriers found";
                            courierSelect.appendChild(option);
                        }
                    }

                    const currentFoodSelects = document.querySelectorAll('.dynamic-food-list');
                    currentFoodSelects.forEach(select => {
                        select.innerHTML = '<option value="">Select Food...</option>';
                        if (data.foods.length > 0) {
                            data.foods.forEach(food => {
                                const option = document.createElement('option');
                                option.value = food.food_id;
                                option.textContent = `${food.item_name} ($${food.price})`;
                                select.appendChild(option);
                            });
                        } else {
                            const option = document.createElement('option');
                            option.textContent = "No menu items found";
                            select.appendChild(option);
                        }
                    });

                })
                .catch(error => console.error('Error fetching data:', error));
        });
    }
});


function showOrderDetails(event, orderId) {
    event.preventDefault(); 
    event.stopPropagation(); 

    const modal = document.getElementById('detailModal');
    const tbody = document.getElementById('modal-items');
    const totalSpan = document.getElementById('grand-total');

    modal.style.display = 'flex';
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">Loading...</td></tr>';

    fetch(`/order_details/${orderId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            tbody.innerHTML = '';
            let grandTotal = 0;
            
            if(data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">No items found in order.</td></tr>';
            } else {
                data.forEach(item => {
                    let row = `
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 10px;">${item.item_name}</td>
                            <td style="padding: 10px;">${item.quantity}</td>
                            <td style="padding: 10px;">$${item.unit_price} </td>
                            <td style="padding: 10px;">$${item.subtotal} </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                    grandTotal += parseFloat(item.subtotal);
                });
            }
            totalSpan.innerText = "$" + grandTotal.toFixed(2);
        })
        .catch(err => {
            console.error("Hata:", err);
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:red; padding:20px;">Error fetching data!</td></tr>';
        });
}

function toggleOrderFields() {
    const typeSelect = document.getElementById('order-type');
    const type = typeSelect ? typeSelect.value : ''; 
    
    const dineInDiv = document.getElementById('dine-in-fields');
    const deliveryDiv = document.getElementById('delivery-fields');
    const foodSection = document.getElementById('food-section'); 

    if (!dineInDiv || !deliveryDiv) return;

    if (type === 'Dine-in') {
        dineInDiv.style.display = 'block';
        deliveryDiv.style.display = 'none';
        
    } else if (type === 'Delivery') {
        dineInDiv.style.display = 'none';
        if(document.getElementById('order-table-no')) document.getElementById('order-table-no').value = '';
        deliveryDiv.style.display = 'block';
        if(foodSection) foodSection.style.display = 'block'; 
        
    } else {
        dineInDiv.style.display = 'block';     
        deliveryDiv.style.display = 'block';   
        if(foodSection) foodSection.style.display = 'none'; 
    }
}

function addFoodRow() {
    const container = document.getElementById('food-items-container');
    const firstRow = container.querySelector('.food-row');
    
    const newRow = firstRow.cloneNode(true);
    
    newRow.querySelector('select').value = "";
    newRow.querySelector('input').value = "1";
    
    if (!newRow.querySelector('.remove-btn')) {
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.innerText = 'X';
        removeBtn.className = 'remove-btn';
        removeBtn.style = "background: #dc3545; color: white; border: none; padding: 0 8px; cursor: pointer; margin-left: 5px;";
        removeBtn.onclick = function() { this.parentElement.remove(); }; 
        newRow.appendChild(removeBtn);
    } else {
         newRow.querySelector('.remove-btn').onclick = function() { this.parentElement.remove(); };
    }

    container.appendChild(newRow);
}

    function calculateLiveTotals() {
        let totalQty = 0;
        let totalAmount = 0;
        let hasSelectedFood = false;

        const rows = document.querySelectorAll('.food-row');
        rows.forEach(row => {
            const select = row.querySelector('select[name="food_id"]');
            const qtyInput = row.querySelector('input[name="quantity"]');
            
            if (select && select.value) {
                hasSelectedFood = true;
                const qty = parseFloat(qtyInput.value) || 0;
                
                const text = select.options[select.selectedIndex].text;
                const match = text.match(/\(\$(\d+(?:\.\d+)?)\)/);
                
                let price = 0;
                if (match) price = parseFloat(match[1]);
                
                totalQty += qty;
                totalAmount += (qty * price);
            }
        });

        const qtyBox = document.getElementById('order-sales-quantity');
        const amtBox = document.getElementById('order-sales-amount');
        const dateBox = document.getElementById('order-date'); 

        if (hasSelectedFood) {
            
            if(qtyBox) {
                qtyBox.value = totalQty;
                qtyBox.readOnly = true;
                qtyBox.style.backgroundColor = "#e9ecef";
                qtyBox.style.cursor = "not-allowed";
                qtyBox.style.color = "#6c757d";
            }
            if(amtBox) {
                amtBox.value = totalAmount.toFixed(2);
                amtBox.readOnly = true;
                amtBox.style.backgroundColor = "#e9ecef";
                amtBox.style.cursor = "not-allowed";
                amtBox.style.color = "#6c757d";
            }
            if(dateBox) {
                const today = new Date().toISOString().split('T')[0]; 
                dateBox.value = today;
                dateBox.readOnly = true;
                dateBox.style.backgroundColor = "#e9ecef";
                dateBox.style.cursor = "not-allowed";
                dateBox.style.color = "#6c757d";
            }

        } else {
            
            if(qtyBox) {
                qtyBox.readOnly = false;
                qtyBox.style.backgroundColor = "white";
                qtyBox.style.cursor = "text";
                qtyBox.style.color = "black";
            }
            if(amtBox) {
                amtBox.readOnly = false;
                amtBox.style.backgroundColor = "white";
                amtBox.style.cursor = "text";
                amtBox.style.color = "black";
            }
            if(dateBox) {
                dateBox.readOnly = false;
                dateBox.style.backgroundColor = "white";
                dateBox.style.cursor = "text";
                dateBox.style.color = "black";
            }
        }
    }

    const foodContainer = document.getElementById('food-items-container');
    if (foodContainer) {
        foodContainer.addEventListener('input', function(e) {
            if (e.target.matches('select') || e.target.matches('input')) {
                calculateLiveTotals();
            }
        });

        foodContainer.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-btn')) {
                setTimeout(calculateLiveTotals, 50); 
            }
        });
    }

function closeModal() {
    document.getElementById('detailModal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('detailModal');
    if (event.target == modal) {
        closeModal();
    }
}