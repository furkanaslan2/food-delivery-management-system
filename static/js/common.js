document.addEventListener("DOMContentLoaded", function () {
    const flashMessages = document.querySelectorAll(".flash-message");
    flashMessages.forEach((msg) => {
        setTimeout(() => {
            msg.style.display = "none";
        }, 5000);
    });

    const actionButtons = document.querySelector('.action-buttons');
    
    if (!actionButtons) return;

    let selectAllBtn = document.getElementById('select-all-btn');
    if (!selectAllBtn) {
        selectAllBtn = document.createElement('button');
        selectAllBtn.type = "button"; 
        
        selectAllBtn.style.display = 'none'; 
        
        selectAllBtn.className = 'filter-button'; 
        selectAllBtn.id = 'select-all-btn';
        selectAllBtn.style.backgroundColor = '#17a2b8'; 
        selectAllBtn.style.color = 'white';
        
        const sortContainer = actionButtons.querySelector('.sort-container');
        if (sortContainer) {
            sortContainer.insertAdjacentElement('afterend', selectAllBtn);
            selectAllBtn.style.marginLeft = '5px'; 
        } else {
            actionButtons.appendChild(selectAllBtn);
            selectAllBtn.style.marginLeft = '5px'; 
        }

        selectAllBtn.innerHTML = 'Select All';
        selectAllBtn.dataset.action = 'select'; 
    }

    function updateSelectAllState() {
        const checkboxes = document.querySelectorAll('.table-card input[type="checkbox"]');
        const total = checkboxes.length;
        
        if (total === 0) return;

        const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;

        if (checkedCount > 0) {
            selectAllBtn.style.display = 'inline-flex';
            
            if (checkedCount === total) {
                selectAllBtn.innerText = "Deselect All";
                selectAllBtn.style.backgroundColor = "#6c757d"; 
                selectAllBtn.dataset.action = "deselect";
            } else {
                selectAllBtn.innerText = "Select All";
                selectAllBtn.style.backgroundColor = "#17a2b8"; 
                selectAllBtn.dataset.action = "select";
            }
        } else {
            selectAllBtn.style.display = 'none';
            
            selectAllBtn.innerText = "Select All";
            selectAllBtn.style.backgroundColor = "#17a2b8";
            selectAllBtn.dataset.action = "select";
        }
    }

    document.addEventListener('change', function(e) {
        if (e.target && e.target.matches('.table-card input[type="checkbox"]')) {
            updateSelectAllState();
        }
    });

    selectAllBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        const checkboxes = document.querySelectorAll('.table-card input[type="checkbox"]');
        const isSelectAction = selectAllBtn.dataset.action === 'select';

        checkboxes.forEach(cb => {
            cb.checked = isSelectAction;
        });
        
        updateSelectAllState();

        if (checkboxes.length > 0) {
            checkboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    
    updateSelectAllState();
});