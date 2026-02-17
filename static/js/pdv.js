// static/js/pdv.js

// Usar uma IIFE (Immediately Invoked Function Expression) para isolar o escopo
// e garantir que o script seja executado apenas uma vez, mesmo se carregado múltiplas vezes.
(function() {
    // Verifica se o script já foi inicializado para evitar duplicação de listeners
    if (window.pdvInitialized) {
        console.warn("PDV script já inicializado. Ignorando nova execução.");
        return;
    }
    window.pdvInitialized = true; // Marca como inicializado

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
        const printReceiptModalElement = document.getElementById('printReceiptModal');
        const printReceiptModal = new bootstrap.Modal(printReceiptModalElement);
        const receiptContent = document.getElementById('receipt-content');
        const printBtn = document.getElementById('print-btn');
        const printAllBtn = document.getElementById('print-all-btn'); // Novo botão para imprimir todos

        let cart = [];
        let currentReceiptsToPrint = []; // Armazena a lista de HTMLs de cupom para impressão

        // Função debounce para limitar a frequência de chamadas de função
        function debounce(func, delay) {
            let timeout;
            return function(...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), delay);
            };
        }

        // Função para buscar produtos
        searchInput.addEventListener('input', debounce(function() {
            const query = searchInput.value.trim();
            if (query.length > 1) {
                fetch(`/pdv/search_product?query=${query}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(products => {
                        searchResults.innerHTML = '';
                        if (products.length > 0) {
                            products.forEach(product => {
                                const li = document.createElement('li');
                                li.classList.add('list-group-item', 'list-group-item-action');
                                li.textContent = `${product.name} (R$ ${product.price.toFixed(2)}) - Estoque: ${product.stock}`;
                                li.dataset.productId = product.id;
                                li.dataset.productName = product.name;
                                li.dataset.productPrice = product.price;
                                li.dataset.productStock = product.stock;
                                li.addEventListener('click', addProductToCart);
                                searchResults.appendChild(li);
                            });
                            searchResults.style.display = 'block';
                        } else {
                            searchResults.style.display = 'none';
                        }
                    })
                    .catch(error => {
                        console.error('Erro ao buscar produtos:', error);
                        searchResults.innerHTML = '<li class="list-group-item text-danger">Erro ao buscar produtos.</li>';
                        searchResults.style.display = 'block';
                    });
            } else {
                searchResults.style.display = 'none';
            }
        }, 300));

        // Função para adicionar produto ao carrinho
        function addProductToCart(event) {
            const productId = parseInt(event.target.dataset.productId);
            const productName = event.target.dataset.productName;
            const productPrice = parseFloat(event.target.dataset.productPrice);
            const productStock = parseInt(event.target.dataset.productStock);

            const existingItem = cart.find(item => item.id === productId);

            if (existingItem) {
                if (existingItem.quantity < productStock) {
                    existingItem.quantity++;
                } else {
                    alert(`Estoque máximo (${productStock}) atingido para ${productName}.`);
                }
            } else {
                if (productStock > 0) {
                    cart.push({
                        id: productId,
                        name: productName,
                        price: productPrice,
                        quantity: 1,
                        stock: productStock // Manter o estoque original para validação
                    });
                } else {
                    alert(`Produto ${productName} sem estoque.`);
                }
            }
            updateCartDisplay();
            searchResults.style.display = 'none'; // Esconde os resultados após adicionar
            searchInput.value = ''; // Limpa o campo de busca
        }

        // Função para remover item do carrinho
        function removeItemFromCart(event) {
            const productId = parseInt(event.target.dataset.id);
            cart = cart.filter(item => item.id !== productId);
            updateCartDisplay();
        }

        // Função para atualizar a exibição do carrinho
        function updateCartDisplay() {
            cartItemsContainer.innerHTML = '';
            let total = 0;

            if (cart.length === 0) {
                cartItemsContainer.innerHTML = '<li class="list-group-item text-center text-muted">Carrinho vazio</li>';
                cartTotalElement.textContent = '0.00';
                checkoutBtn.disabled = true;
                clearCartBtn.disabled = true;
                return;
            }

            cart.forEach(item => {
                const li = document.createElement('li');
                li.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');
                li.innerHTML = `
                    <div>
                        ${item.name} (R$ ${item.price.toFixed(2)})
                        <br>
                        <small>Estoque: ${item.stock}</small>
                    </div>
                    <div class="d-flex align-items-center">
                        <button class="btn btn-sm btn-outline-secondary me-1" data-id="${item.id}" data-action="decrease">-</button>
                        <span class="badge bg-primary rounded-pill me-1">${item.quantity}</span>
                        <button class="btn btn-sm btn-outline-secondary me-1" data-id="${item.id}" data-action="increase">+</button>
                        <button class="btn btn-sm btn-outline-danger" data-id="${item.id}" data-action="remove">x</button>
                    </div>
                `;
                cartItemsContainer.appendChild(li);
                total += item.price * item.quantity;
            });

            cartTotalElement.textContent = total.toFixed(2);
            checkoutBtn.disabled = false;
            clearCartBtn.disabled = false;
            calculateChange(); // Recalcula o troco ao atualizar o carrinho
        }

        // Event listeners para botões de quantidade e remoção no carrinho
        cartItemsContainer.addEventListener('click', function(event) {
            const target = event.target;
            const productId = parseInt(target.dataset.id);
            const action = target.dataset.action;

            if (action === 'increase') {
                const item = cart.find(i => i.id === productId);
                if (item && item.quantity < item.stock) {
                    item.quantity++;
                } else if (item) {
                    alert(`Estoque máximo (${item.stock}) atingido para ${item.name}.`);
                }
            } else if (action === 'decrease') {
                const item = cart.find(i => i.id === productId);
                if (item && item.quantity > 1) {
                    item.quantity--;
                } else if (item) {
                    removeItemFromCart(event); // Remove se a quantidade chegar a 0
                }
            } else if (action === 'remove') {
                removeItemFromCart(event);
            }
            updateCartDisplay();
        });

        // Limpar carrinho
        clearCartBtn.addEventListener('click', function() {
            cart = [];
            updateCartDisplay();
            paidAmountInput.value = '0.00';
            calculateChange();
        });

        // Calcular troco
        paidAmountInput.addEventListener('input', calculateChange);
        paymentMethodSelect.addEventListener('change', calculateChange);

        function calculateChange() {
            const total = parseFloat(cartTotalElement.textContent);
            const paid = parseFloat(paidAmountInput.value) || 0;
            const paymentMethod = paymentMethodSelect.value;

            let change = paid - total;
            changeAmountElement.textContent = `R$ ${change.toFixed(2)}`;

            if (change >= 0) {
                changeAmountElement.classList.remove('text-danger');
                changeAmountElement.classList.add('text-success');
                checkoutBtn.disabled = cart.length === 0; // Habilita se houver itens e troco suficiente
            } else {
                changeAmountElement.classList.remove('text-success');
                changeAmountElement.classList.add('text-danger');
                checkoutBtn.disabled = true; // Desabilita se o valor pago for insuficiente
            }

            // Se o método de pagamento não for dinheiro, não exige valor pago exato
            if (paymentMethod !== 'Dinheiro') {
                checkoutBtn.disabled = cart.length === 0; // Habilita se houver itens
                paidAmountInput.value = total.toFixed(2); // Preenche o valor pago com o total
                changeAmountElement.textContent = 'R$ 0.00';
                changeAmountElement.classList.remove('text-danger');
                changeAmountElement.classList.add('text-success');
            }
        }

        // Finalizar Venda
        checkoutBtn.addEventListener('click', function() {
            if (cart.length === 0) {
                alert('O carrinho está vazio. Adicione produtos para finalizar a venda.');
                return;
            }

            const total = parseFloat(cartTotalElement.textContent);
            const paid = parseFloat(paidAmountInput.value) || 0;
            const paymentMethod = paymentMethodSelect.value;

            if (paid < total && paymentMethod === 'Dinheiro') {
                alert('O valor pago é insuficiente para finalizar a venda em dinheiro.');
                return;
            }

            const saleData = {
                cart: cart.map(item => ({
                    id: item.id,
                    name: item.name,
                    price: item.price,
                    quantity: item.quantity
                })),
                total_amount: total,
                payment_method: paymentMethod,
                paid_amount: paid,
                change_amount: paid - total
            };

            fetch('/pdv/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(saleData)
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message || 'Erro desconhecido no checkout'); });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    currentReceiptsToPrint = data.receipt_htmls; // Armazena a lista de HTMLs
                    if (currentReceiptsToPrint && currentReceiptsToPrint.length > 0) {
                        // Exibe o primeiro cupom no modal para pré-visualização
                        receiptContent.innerHTML = currentReceiptsToPrint[0];
                        printReceiptModal.show();
                        // Habilita/desabilita o botão "Imprimir Todos"
                        printAllBtn.style.display = currentReceiptsToPrint.length > 1 ? 'block' : 'none';
                    } else {
                        alert('Venda finalizada com sucesso, mas nenhum cupom foi gerado.');
                    }

                    // Limpa o carrinho após a venda bem-sucedida
                    cart = [];
                    updateCartDisplay();
                    paidAmountInput.value = '0.00';
                    calculateChange();
                } else {
                    alert(`Erro ao finalizar venda: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Erro no checkout:', error);
                alert(`Ocorreu um erro ao finalizar a venda: ${error.message}`);
            });
        });

        // Função para imprimir um único cupom
        function printSingleReceipt(receiptHtml) {
            const printWindow = window.open('', '_blank');
            printWindow.document.write('<html><head><title>Cupom Fiscal</title>');
            printWindow.document.write('<style>');
            printWindow.document.write(`
                body { font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; margin: 0; padding: 10px; }
                .receipt-container { width: 80mm; margin: 0 auto; border: none; padding: 0; }
                .receipt-header, .receipt-body, .receipt-footer { text-align: center; }
                .receipt-body p, .receipt-footer p { margin: 2px 0; }
                .product-name-highlight { font-weight: bold; }
                hr { border-top: 1px dashed #888; margin: 5px 0; }
                @media print {
                    body { margin: 0; padding: 0; }
                    .receipt-container { border: none; }
                }
            `);
            printWindow.document.write('</style></head><body>');
            printWindow.document.write(receiptHtml);
            printWindow.document.write('</body></html>');
            printWindow.document.close();
            printWindow.focus();
            printWindow.print();
            // printWindow.close(); // Comentado para permitir que o usuário feche manualmente se desejar
        }

        // Event listener para o botão "Imprimir Cupom Atual" (no modal, imprime o cupom atualmente exibido)
        printBtn.addEventListener('click', function() {
            if (currentReceiptsToPrint && currentReceiptsToPrint.length > 0) {
                printSingleReceipt(currentReceiptsToPrint[0]); // Imprime apenas o primeiro cupom exibido no modal
                printReceiptModal.hide(); // Esconde o modal após a impressão
            }
        });

        // Event listener para o novo botão "Imprimir Todos os Cupons"
        if (printAllBtn) { // Verifica se o botão existe
            printAllBtn.addEventListener('click', function() {
                if (currentReceiptsToPrint && currentReceiptsToPrint.length > 0) {
                    currentReceiptsToPrint.forEach(receiptHtml => {
                        printSingleReceipt(receiptHtml); // Imprime cada cupom da lista
                    });
                    printReceiptModal.hide(); // Esconde o modal após a impressão de todos
                }
            });
        }

        // Inicializa a exibição do carrinho ao carregar a página
        updateCartDisplay();
        calculateChange();
    });
})(); // Fim da IIFE
