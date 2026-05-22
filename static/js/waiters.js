document.addEventListener("DOMContentLoaded", function () {
    const waiterCards = document.querySelectorAll('.table-card');

    let lastCheckedBox = null;

    function updateInputs(checkbox) {
        const card = checkbox.closest('.table-card');
        const id = card.querySelector('.waiter-id').textContent.trim();
        const name = card.querySelector('.waiter-name').textContent.trim();
        const email = card.querySelector('.waiter-email').textContent.trim();
        const restaurantId = card.querySelector('.waiter-restaurant-id').textContent.trim();

        document.getElementById('waiter-id').value = id;
        document.getElementById('waiter-name').value = name;
        document.getElementById('waiter-email').value = email;
        document.getElementById('waiter-restaurant-id').value = restaurantId;
        document.getElementById('update-waiter-id').value = id;

        const role = document.getElementById('current-user-role').value;
        const idInput = document.getElementById('waiter-id');
        const resInput = document.getElementById('waiter-restaurant-id');
        
        const inputsToLock = [idInput, resInput];

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
    }

    function clearInputs() {
        document.getElementById('waiter-id').value = '';
        document.getElementById('waiter-name').value = '';
        document.getElementById('waiter-email').value = '';
        document.getElementById('waiter-restaurant-id').value = '';
        document.getElementById('update-waiter-id').value = '';

        const idInput = document.getElementById('waiter-id');
        const resInput = document.getElementById('waiter-restaurant-id');
        
        const inputsToUnlock = [idInput, resInput];

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
    }

    function handleCheckboxChange(event) {
       
        const selectedCheckboxes = document.querySelectorAll('#waiter-list input[type="checkbox"]:checked');

        if (selectedCheckboxes.length === 0) {
            clearInputs();
        } 
        else if (selectedCheckboxes.length === 1) {
            updateInputs(selectedCheckboxes[0]);
        } 
        else {
            clearInputs();
        }
    }

    waiterCards.forEach(card => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', handleCheckboxChange);
    });
});

let matchedCards = [];
let currentMatchIndex = 0;

function searchWaiter() {
    const idInput = document.getElementById('waiter-id').value.trim().toLowerCase();
    const nameInput = document.getElementById('waiter-name').value.trim().toLowerCase();
    const restaurantIdInput = document.getElementById('waiter-restaurant-id').value.trim().toLowerCase();
    const cards = document.querySelectorAll('.table-card');
    matchedCards = [];
    currentMatchIndex = -1;

    if (!idInput && !nameInput && !restaurantIdInput) {
        alert("Please enter at least one search criterion.");
        return;
    }

    cards.forEach(card => card.classList.remove('highlight'));

    cards.forEach(card => {
        const id = card.querySelector('.waiter-id').textContent.toLowerCase();
        const name = card.querySelector('.waiter-name').textContent.toLowerCase();
        const restaurantId = card.querySelector('.waiter-restaurant-id').textContent.toLowerCase();

        if (
            (!idInput || id === idInput) &&
            (!nameInput || name.includes(nameInput)) &&
            (!restaurantIdInput || restaurantId === restaurantIdInput)
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
        alert("No waiter found matching all the criteria exactly.");
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
    document.getElementById('waiter-id').value = "";
    document.getElementById('waiter-name').value = "";
    document.getElementById('waiter-restaurant-id').value = "";

    document.getElementById('clear-filter').value = "true";
    document.getElementById('waiter-form').submit();

    document.querySelectorAll('.table-card').forEach(card => card.classList.remove('highlight'));
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => checkbox.checked = false);

    matchedCards = [];
    currentMatchIndex = 0;

    document.getElementById('navigation').classList.add('hidden');
}

function collectSelected() {
    const selectedWaiters = [];
    const checkboxes = document.querySelectorAll('#waiter-list input[type="checkbox"]:checked');

    checkboxes.forEach(checkbox => {
        selectedWaiters.push(checkbox.value);
    });

    document.getElementById('selected-waiters').value = selectedWaiters.join(',');
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
});