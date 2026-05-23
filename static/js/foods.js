document.addEventListener("DOMContentLoaded", function () {
    const foodCards = document.querySelectorAll('.table-card');
    let lastCheckedBox = null;

    function updateInputs(checkbox) {
        const card = checkbox.closest('.table-card');
        const id = card.querySelector('.food-id')?.textContent.trim() || '';
        const name = card.querySelector('.food-name')?.textContent.trim() || '';

        document.getElementById('food-id').value = id;
        document.getElementById('food-name').value = name;
        document.getElementById('update-food-id').value = id;

        const role = document.getElementById('current-user-role').value;
        const idInput = document.getElementById('food-id');

        if (role !== 'admin') {
            if (idInput) {
                idInput.readOnly = true;
                idInput.style.backgroundColor = "#e9ecef";
                idInput.style.cursor = "not-allowed";
            }
        } else {
            if (idInput) {
                idInput.readOnly = false;
                idInput.style.backgroundColor = "";
                idInput.style.cursor = "";
            }
        }
    }

    function clearInputs() {
        document.getElementById('food-id').value = '';
        document.getElementById('food-name').value = '';
        document.getElementById('update-food-id').value = '';

        const idInput = document.getElementById('food-id');

        if (idInput) {
            idInput.readOnly = false;
            idInput.style.backgroundColor = "";
            idInput.style.cursor = "";
        }
    }

    function handleCheckboxChange(event) {
        const selectedCheckboxes = document.querySelectorAll('#food-list input[type="checkbox"]:checked');

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

    foodCards.forEach(card => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (checkbox) {
            checkbox.addEventListener('change', handleCheckboxChange);
        }
    });
});

function collectSelected() {
    const selectedCheckboxes = document.querySelectorAll('.table-card input[type="checkbox"]:checked');
    const selectedIds = Array.from(selectedCheckboxes).map(checkbox => {
        const card = checkbox.closest('.table-card');
        return card.querySelector('.food-id').textContent.trim();
    });
    
    if (selectedIds.length === 0) {
        alert("Please select at least one food item.");
        return false;
    }
    
    document.getElementById('selected-food-items').value = selectedIds.join(',');
    return true;
}

let matchedCards = [];
let currentMatchIndex = 0;

function searchFood() {
    const idInput = document.getElementById('food-id').value.trim().toLowerCase();
    const nameInput = document.getElementById('food-name').value.trim().toLowerCase();
    const cards = document.querySelectorAll('.table-card');
    matchedCards = [];
    currentMatchIndex = -1;

    if (!idInput && !nameInput) {
        alert("Please enter at least one search criterion.");
        return;
    }

    cards.forEach(card => card.classList.remove('highlight'));

    cards.forEach(card => {
        const id = card.querySelector('.food-id').textContent.trim();
        const name = card.querySelector('.food-name').textContent.toLowerCase();

        if (
            (!idInput || id === idInput) &&
            (!nameInput || name.includes(nameInput))
        ) {
            matchedCards.push(card);
        }
    });

    if (matchedCards.length > 0) {
        document.getElementById('navigation').classList.toggle('hidden', matchedCards.length === 1);
        goToNextMatch();
    } else {
        document.getElementById('navigation').classList.add('hidden');
        alert("No food items found matching the criteria.");
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
    document.getElementById('food-id').value = "";
    document.getElementById('food-name').value = "";
    
    document.getElementById('form-action').value = 'clear';
    document.getElementById('food-form').submit();

    document.querySelectorAll('.table-card').forEach(card => card.classList.remove('highlight'));
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => checkbox.checked = false);

    matchedCards = [];
    currentMatchIndex = 0;

    document.getElementById('navigation').classList.add('hidden');
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
    event.preventDefault();
    event.stopPropagation();
    
    const sortMenu = document.getElementById('sort-menu');
    const overlay = document.getElementById('overlay');
    const button = event.target.closest('.sort-button');
    
    sortMenu.classList.toggle('hidden');
    overlay.classList.toggle('hidden');

    if (!sortMenu.classList.contains('hidden')) {
        const buttonRect = button.getBoundingClientRect();
        
        const top = buttonRect.bottom + window.scrollY;
        const left = buttonRect.left;
        
        sortMenu.style.top = `${top}px`;
        sortMenu.style.left = `${left}px`;
        
        const menuRect = sortMenu.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        
        if (menuRect.right > viewportWidth) {
            sortMenu.style.left = `${viewportWidth - menuRect.width - 20}px`;
        }
    }
}

document.addEventListener("DOMContentLoaded", function() {
    const foodForm = document.getElementById('food-form');
    
    const sortButton = document.querySelector('.sort-button');
    if (sortButton) {
        sortButton.addEventListener('click', toggleSortMenu);
    }

    const overlay = document.getElementById('overlay');
    const sortMenu = document.getElementById('sort-menu');
    if (overlay) {
        overlay.addEventListener('click', function() {
            sortMenu.classList.add('hidden');
            overlay.classList.add('hidden');
        });
    }

    document.addEventListener('click', function(event) {
        if (!event.target.closest('.sort-button') && 
            !event.target.closest('.sort-menu') && 
            !sortMenu.classList.contains('hidden')) {
            sortMenu.classList.add('hidden');
            overlay.classList.add('hidden');
        }
    });

    sortMenu.addEventListener('click', function(event) {
        event.stopPropagation();
    });

    ['add-button', 'delete-button', 'update-button', 'filter-button'].forEach(buttonClass => {
        const button = document.querySelector('.' + buttonClass);
        if (button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const action = this.getAttribute('value');
                
                if (action === 'delete' && !collectSelected()) {
                    return;
                }
                
                if (action === 'update' && !document.getElementById('update-food-id').value) {
                    alert('Please select a food item to update.');
                    return;
                }
                
                document.getElementById('form-action').value = action;
                foodForm.submit();
            });
        }
    });
});