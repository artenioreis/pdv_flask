// static/js/pdv.js
(function() {
    if (window.pdvInitialized) return;
    window.pdvInitialized = true;

    document.addEventListener('DOMContentLoaded', function() {
        const searchInput = document.getElementById('product-search');
        const searchResults = document.getElementById('search-results');
        const cartItemsContainer = document.getElementById('cart-items');
        const cartTotalElement = document.getElementById('cart-total');
        const checkoutBtn = document.getElementById('checkout-btn');
        const paymentMethodSelect = document.getElementById('payment-method');
        const paidAmountInput = document.getElementById('paid-amount');
        const changeAmountElement = document.getElementById('change-amount');
        const clearCartBtn = document.getElementById('clear-cart-btn');
        const printReceiptModal = new bootstrap.Modal(document.getElementById('printReceiptModal'));
        const receiptContent = document.getElementById('receipt-content');
        const printAllBtn = document.getElementById('print-all-btn');

        let cart = [];
        let receipts = [];

        // Atalhos de Teclado
        document.addEventListener('keydown', e => {
            if (e.key === 'F2') { e.preventDefault(); searchInput.focus(); }
            if (e.key === 'F4' && !clearCartBtn.disabled) { e.preventDefault(); clearCartBtn.click(); }
            if (e.key === 'F10' && !checkoutBtn.disabled) { e.preventDefault(); checkoutBtn.click(); }
            
            // Navegação simples na busca com setas
            if (searchResults.style.display === 'block') {
                const items = searchResults.querySelectorAll('li');
                let active = Array.from(items).indexOf(document.activeElement);
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (active < items.length - 1) items[active + 1].focus();
                    else items[0].focus();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (active > 0) items[active - 1].focus();
                    else items[items.length - 1].focus();
                }
            }
        });

        // Adicionar com Enter
        searchInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const first = searchResults.querySelector('li');
                if (first) first.click();
            }
        });

        // Função Global para Ajustar Quantidade
        window.changeQuantity = function(id, delta) {
            const item = cart.find(i => i.id === id);
            if (item) {
                if (delta > 0) {
                    // Verifica estoque (precisamos do estoque original que veio na busca)
                    if (item.quantity < item.stock) {
                        item.quantity += delta;
                    } else {
                        alert('Limite de estoque atingido');
                    }
                } else {
                    item.quantity += delta;
                    if (item.quantity <= 0) {
                        removeItem(id);
                        return;
                    }
                }
                updateCart();
            }
        };

        // Função Global para Deletar Item
        window.removeItem = function(id) {
            cart = cart.filter(i => i.id !== id);
            updateCart();
        };

        function updateCart() {
            cartItemsContainer.innerHTML = cart.length ? '' : '<li class="list-group-item text-center text-muted">Carrinho vazio</li>';
            let total = 0;
            cart.forEach(item => {
                const li = document.createElement('li');
                li.className = 'list-group-item d-flex justify-content-between align-items-center';
                li.innerHTML = `
                    <div style="font-weight: bold;">
                        ${item.name}
                        <div class="mt-1">
                            <button class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="changeQuantity(${item.id}, -1)">-</button>
                            <span class="mx-2">${item.quantity}x</span>
                            <button class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="changeQuantity(${item.id}, 1)">+</button>
                        </div>
                    </div>
                    <div>
                        <span class="badge bg-dark me-2">R$ ${(item.price * item.quantity).toFixed(2)}</span>
                        <button class="btn btn-sm btn-danger" onclick="removeItem(${item.id})">X</button>
                    </div>`;
                cartItemsContainer.appendChild(li);
                total += item.price * item.quantity;
            });
            
            const totalStr = total.toFixed(2);
            cartTotalElement.textContent = totalStr;
            
            if (cart.length > 0) {
                paidAmountInput.value = totalStr;
            } else {
                paidAmountInput.value = "0.00";
            }
            
            calculateChange();
        }

        function calculateChange() {
            const total = parseFloat(cartTotalElement.textContent) || 0;
            const paid = parseFloat(paidAmountInput.value) || 0;
            const method = paymentMethodSelect.value;
            const change = paid - total;

            changeAmountElement.textContent = `R$ ${change.toFixed(2)}`;
            
            if (cart.length === 0) {
                checkoutBtn.disabled = true;
                clearCartBtn.disabled = true;
                changeAmountElement.className = 'text-muted';
            } else {
                clearCartBtn.disabled = false;
                if (method === 'Dinheiro') {
                    if (change >= 0) {
                        checkoutBtn.disabled = false;
                        changeAmountElement.className = 'text-success font-weight-bold';
                    } else {
                        checkoutBtn.disabled = true;
                        changeAmountElement.className = 'text-danger';
                    }
                } else {
                    checkoutBtn.disabled = false;
                    changeAmountElement.className = 'text-success';
                }
            }
        }

        paidAmountInput.oninput = calculateChange;
        paymentMethodSelect.onchange = calculateChange;

        clearCartBtn.onclick = () => { 
            if(confirm("Deseja realmente limpar o carrinho?")) {
                cart = []; 
                updateCart(); 
            }
        };

        searchInput.oninput = () => {
            const q = searchInput.value.trim();
            if (q.length > 0) {
                fetch(`/pdv/search_product?query=${q}`).then(r => r.json()).then(data => {
                    searchResults.innerHTML = '';
                    if (data.length > 0) {
                        data.forEach(p => {
                            const li = document.createElement('li');
                            li.className = 'list-group-item list-group-item-action';
                            li.setAttribute('tabindex', '0');
                            li.textContent = `[${p.id}] ${p.name} - R$ ${p.price.toFixed(2)} (Estoque: ${p.stock})`;
                            li.onclick = () => {
                                const ex = cart.find(i => i.id === p.id);
                                if (ex) {
                                    if(ex.quantity < p.stock) ex.quantity++;
                                    else alert('Limite de estoque atingido');
                                } else {
                                    if(p.stock > 0) cart.push({...p, quantity: 1});
                                    else alert('Produto sem estoque');
                                }
                                updateCart(); searchInput.value = ''; searchResults.style.display = 'none'; searchInput.focus();
                            };
                            // Suporte a seleção por teclado nos resultados
                            li.onkeydown = (e) => { if(e.key === 'Enter') li.click(); };
                            searchResults.appendChild(li);
                        });
                        searchResults.style.display = 'block';
                    } else {
                        searchResults.style.display = 'none';
                    }
                });
            } else searchResults.style.display = 'none';
        };

        checkoutBtn.onclick = () => {
            const total = parseFloat(cartTotalElement.textContent);
            const paid = parseFloat(paidAmountInput.value) || 0;
            const data = { 
                cart, 
                total_amount: total, 
                payment_method: paymentMethodSelect.value, 
                paid_amount: paid, 
                change_amount: paid - total 
            };
            
            fetch('/pdv/checkout', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify(data) 
            })
            .then(r => r.json()).then(res => {
                if (res.success) {
                    receipts = res.receipt_htmls;
                    receiptContent.innerHTML = receipts.join('<hr style="border-top: 2px dashed #000; margin: 30px 0;">');
                    printReceiptModal.show();
                    printAllReceipts();
                    cart = []; 
                    updateCart();
                } else alert('Erro: ' + res.message);
            })
            .catch(() => alert('Erro na comunicação com o servidor'));
        };

        function printAllReceipts() {
            const win = window.open('', '_blank');
            win.document.write('<html><head><title>Imprimir Cupons</title></head><body>');
            receipts.forEach((html, index) => {
                win.document.write(html);
                if (index < receipts.length - 1) {
                    win.document.write('<div style="page-break-after: always;"></div>');
                }
            });
            win.document.write('</body></html>');
            win.document.close();
            win.focus();
            setTimeout(() => {
                win.print();
                win.close();
            }, 500);
        }

        printAllBtn.onclick = () => printAllReceipts();

        updateCart();
    });
})();