/* $(function(){ */

function getUserBalance() {
    
    $.get('/wallet/balance', null, null, 'json')
        .done(function(data) {
            let d = [];        
            
            $.each(data.balance, function(k, v) {
                d.push( {id_currency : v.id_currency, 
                    currency_name: v.currency_name, 
                    balance : parseFloat(v.balance).toFixed(2), 
                    balance_award : parseFloat(v.balance_award).toFixed(2),
                    balance_bonus : parseFloat(v.balance_bonus).toFixed(2),
                });
                if(v.id_status != 'AC'){
                    Swal.fire({
                    title: '<p class="fs-20 fw-5 blue">Estimado jugador </p><p class="fs-25 fw-7 blue"> ¡Active su usuario! </p><p class="fs-25 fw-5 blue">Comuníquese con nuestro soporte</p>', // Modal title
                    iconHtml: '<img src="/LotoGame_files/activate.webp">', // Custom icon
                    customClass: {
                        icon: 'no-border', // Custom class for the icon
                    },
                    confirmButtonColor: '#3085d6', // Confirm button color
                    confirmButtonText: 'Soporte', // Confirm button text
                    }).then((result) => {
                    if (result.isConfirmed) {
                        window.location.href = "https://secure.loteriadehoy.com/logout"; // Simulate a click on the install button if the user confirms
                    } else {
                        window.location.href = "https://secure.loteriadehoy.com/logout";
                    }
                    });
                }
            });
            this.bts = data.ts;
            $(document).trigger('userbalance.update', { balances: d, ts: this.bts });
        }).fail(function() {
            $(document).trigger('userbalance.fail', {});
        });

        $(document).on('userbalance.update', function(e, f) {
            $.each(f.balances, function(k, v) {
                let t = `${v.currency_name}&nbsp;&nbsp;&nbsp;&nbsp;(${parseFloat(v.balance,2) + parseFloat(v.balance_award,2) + parseFloat(v.balance_bonus,2)} ${v.id_currency})`;
                let amount = 0;
                let b = parseFloat(v.balance);
                let ba = parseFloat(v.balance_award);
                let bb = parseFloat(v.balance_bonus);
                //console.log(b + ba + bb, b + ba, b,  ba, bb);
                if((b + ba + bb) > 0){
                    amount = (b + ba + bb).toLocaleString();
                }
                $(`select.loto-walletbalance option[data-cid='${v.id_currency}']`).html(t);
                if (v.id_currency=="VES") { $('.ves').html(amount); };
                if (v.id_currency=="USD") { $('.usd').html(amount); };
                if (v.id_currency=="USDT") { $('.usdt').html(amount); };
            });

        });
}
getUserBalance();
/** 
 * @todo reactivate when needed
*/
//setInterval(getUserBalance, 10000);

/*});  */