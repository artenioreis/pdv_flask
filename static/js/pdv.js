// static/js/pdv.js
document.addEventListener('DOMContentLoaded', function() {
    const productSearch = document.getElementById('productSearch');
    const searchResults = document.getElementById('searchResults');
    const cartItems = document.getElementById('cartItems');
    const cartTotalSpan = document.getElementById('cartTotal');
    const clearCartBtn = document.getElementById('clearCartBtn');
    const checkoutBtn = document.getElementById('checkoutBtn');
    const paymentMethodSelect = document.getElementById('paymentMethod');
    const paidAmountInput = document.getElementById('paidAmount');
    const paidAmountGroup = document.getElementById('paidAmountGroup'); // O grupo para mostrar/esconder
    const changeAmountInput = document.getElementById('changeAmount');
    const receiptModal = new bootstrap.Modal(document.getElementById('receiptModal'));
    const receiptContent = document.getElementById('receiptContent');
    const printReceiptBtn = document.getElementById('printReceiptBtn');

    let cart = []; // Array para armazenar os itens do carrinho

    // --- Funções de Utilitário ---
    function formatCurrency(value) {
        return parseFloat(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function parseCurrency(value) {
        // Remove o símbolo da moeda, pontos de milhar e substitui vírgula por ponto decimal
        return parseFloat(value.replace(/[R$ ]/g, '').replace('.', '').replace(',', '.'));
    }

    // --- Atualiza o Display do Carrinho ---
    function updateCartDisplay() {
        cartItems.innerHTML = '';
        let total = 0;

        if (cart.length === 0) {
            cartItems.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Carrinho vazio.</td></tr>';
        } else {
            cart.forEach((item, index) => {
                const subtotal = item.price * item.quantity;
                total += subtotal;

                const row = `
                    <tr>
                        <td>${item.name}</td>
                        <td>
                            <input type="number" class="form-control form-control-sm quantity-input"
                                value="${item.quantity}" min="1" data-index="${index}">
                        </td>
                        <td>${formatCurrency(item.price)}</td>
                        <td>${formatCurrency(subtotal)}</td>
                        <td>
                            <button class="btn btn-danger btn-sm remove-item-btn" data-index="${index}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
                cartItems.innerHTML += row;
            });
        }

        cartTotalSpan.textContent = formatCurrency(total);
        updatePaymentDetails(total); // Atualiza os detalhes de pagamento e troco
    }

    // --- Adiciona Produto ao Carrinho ---
    function addProductToCart(product) {
        const existingItem = cart.find(item => item.id === product.id);
        if (existingItem) {
            if (existingItem.quantity < product.stock) {
                existingItem.quantity++;
                flashMessage(`Quantidade de "${product.name}" atualizada no carrinho.`, 'info');
            } else {
                flashMessage(`Estoque máximo de "${product.name}" atingido.`, 'warning');
            }
        } else {
            if (product.stock > 0) {
                cart.push({
                    id: product.id,
                    name: product.name,
                    price: product.price,
                    stock: product.stock, // Mantém o estoque original para validação
                    quantity: 1
                });
                flashMessage(`"${product.name}" adicionado ao carrinho.`, 'success');
            } else {
                flashMessage(`"${product.name}" está fora de estoque.`, 'danger');
            }
        }
        updateCartDisplay();
        productSearch.value = ''; // Limpa o campo de busca
        searchResults.innerHTML = ''; // Limpa os resultados da busca
    }

    // --- Atualiza Detalhes de Pagamento e Troco ---
    function updatePaymentDetails(total) {
        const paymentMethod = paymentMethodSelect.value;
        let paidAmount = parseFloat(paidAmountInput.value) || 0; // Garante que seja um número, 0 se vazio

        // Se o método não for Dinheiro, o valor pago é igual ao total da venda
        if (paymentMethod !== 'Dinheiro') {
            paidAmountGroup.style.display = 'none'; // Esconde o campo de valor pago
            paidAmount = total; // Valor pago é o total da venda
            paidAmountInput.value = total.toFixed(2); // Atualiza o input (mesmo que escondido)
        } else {
            paidAmountGroup.style.display = 'block'; // Mostra o campo de valor pago
            // Se o campo de valor pago estiver vazio, define como 0 para o cálculo
            if (paidAmountInput.value === '' || isNaN(paidAmount)) {
                paidAmountInput.value = '0.00';
                paidAmount = 0;
            }
        }

        const change = paidAmount - total;
        changeAmountInput.value = change.toFixed(2); // Formata para 2 casas decimais

        // Adiciona classe para indicar troco negativo (a pagar) ou positivo (a devolver)
        if (change < 0) {
            changeAmountInput.classList.remove('text-success');
            changeAmountInput.classList.add('text-danger');
        } else {
            changeAmountInput.classList.remove('text-danger');
            changeAmountInput.classList.add('text-success');
        }
    }

    // --- Mensagens Flash (para substituir flash do Flask no frontend) ---
    function flashMessage(message, category) {
        const alertContainer = document.querySelector('.container-fluid.py-4'); // Ou onde você preferir
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${category} alert-dismissible fade show mt-3`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.prepend(alertDiv); // Adiciona no topo do container
        setTimeout(() => alertDiv.remove(), 5000); // Remove após 5 segundos
    }

    // --- Event Listeners ---

    // Busca de produtos
    productSearch.addEventListener('input', function() {
        const query = this.value.trim();
        if (query.length > 1) {
            fetch(`/pdv/search_product?query=${query}`)
                .then(response => response.json())
                .then(products => {
                    searchResults.innerHTML = '';
                    if (products.length > 0) {
                        products.forEach(product => {
                            const item = document.createElement('a');
                            item.href = '#';
                            item.classList.add('list-group-item', 'list-group-item-action');
                            item.textContent = `${product.name} (R$ ${product.price.toFixed(2)}) - Estoque: ${product.stock}`;
                            item.addEventListener('click', function(e) {
                                e.preventDefault();
                                addProductToCart(product);
                            });
                            searchResults.appendChild(item);
                        });
                    } else {
                        searchResults.innerHTML = '<a href="#" class="list-group-item list-group-item-action disabled">Nenhum produto encontrado.</a>';
                    }
                })
                .catch(error => {
                    console.error('Erro na busca de produtos:', error);
                    searchResults.innerHTML = '<a href="#" class="list-group-item list-group-item-action disabled text-danger">Erro ao buscar produtos.</a>';
                });
        } else {
            searchResults.innerHTML = '';
        }
    });

    // Atualiza quantidade no carrinho
    cartItems.addEventListener('change', function(e) {
        if (e.target.classList.contains('quantity-input')) {
            const index = parseInt(e.target.dataset.index);
            let newQuantity = parseInt(e.target.value);

            if (isNaN(newQuantity) || newQuantity < 1) {
                newQuantity = 1;
                e.target.value = 1;
            }

            const item = cart[index];
            if (newQuantity > item.stock) {
                flashMessage(`Quantidade máxima para "${item.name}" é ${item.stock}.`, 'warning');
                newQuantity = item.stock;
                e.target.value = item.stock;
            }
            item.quantity = newQuantity;
            updateCartDisplay();
        }
    });

    // Remove item do carrinho
    cartItems.addEventListener('click', function(e) {
        if (e.target.closest('.remove-item-btn')) {
            const index = parseInt(e.target.closest('.remove-item-btn').dataset.index);
            const removedItem = cart.splice(index, 1);
            flashMessage(`"${removedItem[0].name}" removido do carrinho.`, 'info');
            updateCartDisplay();
        }
    });

    // Limpar carrinho
    clearCartBtn.addEventListener('click', function() {
        if (confirm('Tem certeza que deseja limpar o carrinho?')) {
            cart = [];
            updateCartDisplay();
            flashMessage('Carrinho limpo.', 'info');
        }
    });

    // Finalizar Venda
    checkoutBtn.addEventListener('click', function() {
        if (cart.length === 0) {
            flashMessage('O carrinho está vazio. Adicione produtos para finalizar a venda.', 'warning');
            return;
        }

        const totalAmount = parseCurrency(cartTotalSpan.textContent);
        const paymentMethod = paymentMethodSelect.value;
        let paidAmount = parseFloat(paidAmountInput.value) || 0; // Garante que seja um número, 0 se vazio
        const changeAmount = parseFloat(changeAmountInput.value) || 0; // Garante que seja um número, 0 se vazio

        // Validação adicional no frontend para pagamento em dinheiro
        if (paymentMethod === 'Dinheiro' && paidAmount < totalAmount) {
            flashMessage('Valor pago insuficiente para pagamento em dinheiro.', 'danger');
            return;
        }

        // Se não for dinheiro, o valor pago é o total da venda
        if (paymentMethod !== 'Dinheiro') {
            paidAmount = totalAmount;
        }

        fetch('/pdv/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cart: cart,
                payment_method: paymentMethod,
                total_amount: totalAmount,
                paid_amount: paidAmount, // Envia o valor pago
                change_amount: changeAmount // Envia o troco
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                flashMessage(data.message, 'success');
                cart = []; // Limpa o carrinho após a venda
                updateCartDisplay();

                // Exibe o(s) cupom(ns) no modal
                receiptContent.innerHTML = data.receipt_htmls.join('<hr style="border-top: 1px dashed #ccc;">'); // Junta múltiplos cupons
                receiptModal.show();
            } else {
                flashMessage(data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Erro ao finalizar venda:', error);
            flashMessage('Erro de conexão ao finalizar a venda.', 'danger');
        });
    });

    // Atualiza detalhes de pagamento ao mudar o método
    paymentMethodSelect.addEventListener('change', function() {
        updatePaymentDetails(parseCurrency(cartTotalSpan.textContent));
    });

    // Atualiza detalhes de pagamento ao digitar o valor pago
    paidAmountInput.addEventListener('input', function() {
        updatePaymentDetails(parseCurrency(cartTotalSpan.textContent));
    });

    // Função para imprimir o conteúdo do modal
    printReceiptBtn.addEventListener('click', function() {
        const printWindow = window.open('', '_blank');
        printWindow.document.write('<html><head><title>Cupom</title>');
        printWindow.document.write('<style>');
        printWindow.document.write('body { font-family: "Courier New", Courier, monospace; font-size: 12px; margin: 0; padding: 10px; }');
        printWindow.document.write('hr { border-top: 1px dashed #ccc; margin: 10px 0; }');
        printWindow.document.write('</style>');
        printWindow.document.write('</head><body>');
        printWindow.document.write(receiptContent.innerHTML);
        printWindow.document.write('</body></html>');
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
        // printWindow.close(); // Opcional: fechar a janela após a impressão
    });

    // Inicializa o display do carrinho e detalhes de pagamento
    updateCartDisplay();
});
