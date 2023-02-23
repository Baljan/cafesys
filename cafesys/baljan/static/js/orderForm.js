function calcSum() {
    var grandTotal=0;

    $(".order-item").each(function() {
        var amount = parseInt($(this).find("input").val());
        var cost = parseInt($(this).find(".cost").text());
        var total = amount * cost;

        if (isNaN(total)) {
            total = 0;
        }

        $(this).find(".total").text(total.toString());

        if (!$(this).hasClass("exclude-from-total")) {
            grandTotal+=total;
        }
    });

    $('#currentSum').text(grandTotal);
    $('#id_orderSum').val(grandTotal);
}

function calcGroupAmnt(groupName) {
    var groupAmnt = 0;
    var subItemClass = "." + groupName + "-sub-item";

    $(subItemClass).each(function() {
        var amount = parseInt($(this).find("input").val());

        if (isNaN(amount)) {
            amount = 0;
        }

        groupAmnt += amount;
    });

    if (groupAmnt === 0) {
        groupAmnt = "";
    }

    $("#" + groupName).find("input").val(groupAmnt);

    return groupAmnt;
}

function disablePickupFields(disable) {
    var pickupName = $('#id_pickupName');
    var pickupEmail = $('#id_pickupEmail');
    var pickupNumber = $('#id_pickupNumber');

    pickupName.prop('readonly', disable);
    pickupEmail.prop('readonly', disable);
    pickupNumber.prop('readonly', disable);

    if (disable){
        pickupName.val($('#id_orderer').val());
        pickupEmail.val($('#id_ordererEmail').val());
        pickupNumber.val($('#id_phoneNumber').val());
    }else{
        pickupName.val("");
        pickupEmail.val("");
        pickupNumber.val("");
    }
}

function clearWindowField(name){
    $('#' + name + 'Modal :input').each(function() {
        $(this).val('');
    });
    $('#id_numberOf'+ name).val('');  
    $('#'+ name+ 'Sum').html(''); 
    calcSum();
}

window.onload = function justdoit() {
    var sameAsOrderer = $("#id_sameAsOrderer");
    if (sameAsOrderer.is(':checked')) {
        disablePickupFields(true);
    }

    sameAsOrderer.on('change', function () {
        if ($(this).is(':checked')) {
            disablePickupFields(true);
        }
        else {
            disablePickupFields(false);
        }
    
    });

    $('#id_orderer').on('change', function () {
        if ($("#id_sameAsOrderer").is(':checked')) {
            $('#id_pickupName').val($('#id_orderer').val());
        }
    });
    $('#id_ordererEmail').on('change',function () {
        if ($("#id_sameAsOrderer").is(':checked')) {
            $('#id_pickupEmail').val($('#id_ordererEmail').val());
        }
    });
    $('#id_phoneNumber').on('change', function () {
        if ($("#id_sameAsOrderer").is(':checked')) {
            $('#id_pickupNumber').val($('#id_phoneNumber').val());
        }
    });

    $("#form-confirmation1, #form-confirmation2").on('change', function () {
        var checked1 = $("#form-confirmation1").is(':checked');
        var checked2 = $("#form-confirmation2").is(':checked');
        $("#submit-button").prop('disabled', !(checked1 && checked2));
    });
};

$(function () {
    $(".order-group").each(function() {
        let groupId = $(this).attr('id');
        let subItemClass = "." + groupId + "-sub-item";
        let groupCost = parseInt($(this).find(".cost").text());
        let groupSumElem = $("#" + groupId + "Sum");

        $(subItemClass).on("input", function() {
            let groupAmnt = calcGroupAmnt(groupId);
            groupSumElem.text(groupAmnt*groupCost);
        });
    });

    $(".order-item").on('input', function () {
        calcSum();
        if(window.onbeforeunload === null) {
            window.onbeforeunload = function() {
                return "";
            }
        }
    });

    //  Set max limit on products depending on chosen pickup time
    //  0 ,'Morgon 07:30-08:00'
    //  1,'Lunch 12:15-13:00')
    //  2,'Eftermiddag 16:15-17:00'
    $('#id_pickup').change(function() {
        var value = $('#id_pickup').val();
        $("#order_error").html("");

        if(value == 0){
            $('#id_numberOfCoffee').attr('max', 45);
            if($('#id_numberOfCoffee').val() > 45)
                $('#id_numberOfCoffee').val(45);
            $('#Pastasalad').show();

        }else if(value == 1){
            $('#id_numberOfCoffee').attr('max', 90);
            if($('#id_numberOfCoffee').val() > 90){
                $('#id_numberOfCoffee').val(90);
            }
            $('#Pastasalad').hide();
            clearWindowField('Pastasalad');
            
            if($('#id_numberOfJochen').val() > 100){
                clearWindowField('Jochen')
                var error_msg = "Det går inte beställa mer än 100st jochen till " + $('#id_pickup option:selected').text()+ ".";
                $("#order_error").html("<p class='text-danger'>" + error_msg + "</p>");
            }
        }else{
            $('#id_numberOfCoffee').attr('max', 135);
            if($('#id_numberOfCoffee').val() > 135){
                $('#id_numberOfCoffee').val(135);
            }
            $('#Pastasalad').hide();
            clearWindowField('Pastasalad');

            if($('#id_numberOfJochen').val() > 100){
                clearWindowField('Jochen')
                var error_msg = "Det går inte beställa mer än 100st jochen till " + $('#id_pickup option:selected').text()+ ".";
                $("#order_error").html("<p class='text-danger'>" + error_msg + "</p>");
            }
        }
    });

    // Sets max limit on Jochen for afternoon and evening
    const inputs = $('#JochenModal').find("input[type='number']");
    const buttons = $('#JochenModal').find("button");
    var value = $('#id_pickup').val();
    const amount = 100;
    
    inputs.on("input", function() {
        if($('#id_pickup').val()== 1 || $('#id_pickup').val() == 2){
            let sum = 0;
            inputs.each(function() {
                sum += parseInt($(this).val()) || 0; 
            });
            if(sum > amount){
                buttons.prop("disabled", true);
                var error_msg = "Det går inte beställa mer än 100st jochen till " + $('#id_pickup option:selected').text()+ ".";
                $("#Jochen_error").html("<p class='text-danger'>" + error_msg + "</p>");
            } else {
                buttons.prop("disabled", false);
                $("#Jochen_error").html("");
            }
        }
    });

    //Controll that chosen date is valid for order pastasallad, jochen and minijochen.
    $('#id_date').on("change", function() { 
        var selectedDate = new Date($(this).val());
        var today = new Date();
        var thursday = new Date(today.setDate(today.getDate() + (4 + 7 - today.getDay()) % 7));
    
        if (selectedDate <= thursday) {
            $('#Pastasalad').hide();
            $('#Jochen').hide();
            $('#Minijochen').hide();

            if($('#id_numberOfPastasalad').val() != "" || $('#id_numberOfJochen').val() != "" || $('#id_numberOfMinijochen').val() != ""){
                var error_msg = "Orderdatumet är för nära inpå för kunna beställa pastasallad, jochen eller minijochen.";
                $("#order_error").html("<p class='text-danger'>" + error_msg + "</p>");
                clearWindowField('Jochen');
                clearWindowField('Minijochen');
                clearWindowField('Pastasalad');
            }
        } else {
            $('#Pastasalad').show();
            $("#Jochen").show();
            $('#Minijochen').show();
            $("#order_error").html("");
        }
    });

    $("form").on("submit", function() {
        window.onbeforeunload = null;
    });

    calcSum();
});


