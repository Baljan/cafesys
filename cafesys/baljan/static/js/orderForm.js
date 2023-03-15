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

function getWeekNumber(date) {
    var d = new Date(date);
    d.setHours(0, 0, 0, 0);
    // Set to nearest Thursday: current date + 4 - current day number
    // Make Sunday's day number 7
    d.setDate(d.getDate() + 4 - (d.getDay()||7));
    // Get first day of year
    var yearStart = new Date(d.getFullYear(),0,1);
    // Calculate full weeks to nearest Thursday
    var weekNo = Math.ceil(( ( (d - yearStart) / 86400000) + 1)/7);
    return weekNo;
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

function changeLimit(name, limit, error_msg){
    $('#' + name).attr('max', limit);
        if($('#' + name).val() > limit){
            $('#' + name).val(limit);
            setErrorMsg(error_msg, "order_error")
        }
}

function validDate(){
    var selectedDate = new Date($("#id_date").val());
    var now = new Date();
        
    var selectedWeek = getWeekNumber(selectedDate);
    console.log(selectedWeek)
    var currentWeek = getWeekNumber(now);
    console.log(currentWeek)
    var nextWeek = currentWeek + 1; 
    var nextWeekInvalid = (selectedWeek == nextWeek && (now.getDay() > 4 || now.getDay() == 0));
    console.log("Day " + now.getDay())
    console.log("nextweekinvalid " + nextWeekInvalid)

    if (selectedWeek == currentWeek || nextWeekInvalid) {
        return false
    }else {
        return true
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

function setErrorMsg(text, field){
    var temp = $("#order_error").text()
    $('#'+ field).html("<p class='text-danger'>" + text + "<br>" + temp + "</p>");
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
    //  1 ,'Morgon 07:30-08:00'
    //  2,'Lunch 12:15-13:00')
    //  3,'Eftermiddag 16:15-17:00'
    $('#id_pickup').change(function() {
        var value = $('#id_pickup').val();
        $("#order_error").html("");
        
        if(value == 0){
            changeLimit('id_numberOfCoffee', 135, '');

        }else if(value == 1){
            changeLimit('id_numberOfCoffee', 45,'Det går inte beställa mer än 45 koppar kaffe till ' + $('#id_pickup option:selected').text()+ '.');
            if(validDate()){
                $('#Pastasalad').show();
            }

        }else if(value == 2){
            changeLimit('id_numberOfCoffee', 90,'Det går inte beställa mer än 90 koppar kaffe till ' + $('#id_pickup option:selected').text()+'.');

            $('#Pastasalad').hide();
            clearWindowField('Pastasalad');
            
            if($('#id_numberOfJochen').val() > 100){
                clearWindowField('Jochen')
                var error_msg = "Det går inte beställa mer än 100st jochen till " + $('#id_pickup option:selected').text()+ ".";
                setErrorMsg(error_msg, "order_error");
            }
        }else if(value == 3){
            changeLimit('id_numberOfCoffee', 135,'Det går inte beställa mer än 135 koppar kaffe till ' + $('#id_pickup option:selected').text()+ '.');
            
            $('#Pastasalad').hide();
            clearWindowField('Pastasalad');

            if($('#id_numberOfJochen').val() > 100){
                clearWindowField('Jochen')
                var error_msg = "Det går inte beställa mer än 100st jochen till " + $('#id_pickup option:selected').text()+ ".";
                setErrorMsg(error_msg, "order_error");
            }
        }
    });

    // Sets max limit on Jochen for afternoon and evening
    const inputs = $('#JochenModal').find("input[type='number']");
    const buttons = $('#JochenModal').find("button");
    var value = $('#id_pickup').val();
    const amount = 100;
    
    inputs.on("input", function() {
        if($('#id_pickup').val()== 2 || $('#id_pickup').val() == 3){
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

    //disable booking food such as sallad and jochen for same week or next week if after thursday
    $('#id_date').on("change", function() { 
        if(validDate()){
            $('#Pastasalad').show();
            $("#Jochen").show();
            $('#Minijochen').show();
            $("#order_error").html("");
        }else{
            $('#Pastasalad').hide();
            $('#Jochen').hide();
            $('#Minijochen').hide();
            
            if($('#id_numberOfPastasalad').val() != "" || $('#id_numberOfJochen').val() != "" || $('#id_numberOfMinijochen').val() != ""){
                var error_msg = "Orderdatumet är för nära inpå för att kunna beställa pastasallad, jochen eller minijochen.";
                setErrorMsg(error_msg, "order_error")
                clearWindowField('Jochen');
                clearWindowField('Minijochen');
                clearWindowField('Pastasalad');
            }
        }
    });

    $("form").on("submit", function() {
        window.onbeforeunload = null;
    });

    calcSum();
});


