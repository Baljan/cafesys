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

function changeLimit(name, limit, error_msg){
    $('#' + name).attr('max', limit);
        if($('#' + name).val() > limit){
            $('#' + name).val(limit);
            setErrorMsg(error_msg, "order_error")
        }
}

// Deadline for jochen and pasta salad comes from the server.
function validDate(){
    var field = $("#id_date");
    var selected = field.val();
    var earliest = field.attr("data-earliest-food-date");

    if (!selected || !earliest) {
        return false;
    }
    return selected >= earliest;
}

// Greys out a product; returns true if anything was cleared.
function setAvailable(name, available){
    var cleared = !available && $('#id_numberOf' + name).val() != "";

    $('#' + name).toggleClass('text-muted', !available)
        .find('input, button').prop('disabled', !available);
    if (!available) {
        clearWindowField(name);
    }
    return cleared;
}

function tooManyJochenForPickup(){
    var pickup = $('#id_pickup').val();
    return (pickup == 2 || pickup == 3) && parseInt($('#id_numberOfJochen').val()) > 100;
}

// Clears jochen if there are too many for the chosen pickup; returns true if it did.
function dropExcessJochen(){
    var drop = tooManyJochenForPickup();
    if (drop) {
        clearWindowField('Jochen');
    }
    return drop;
}

function updateFoodAvailability(droppedJochen){
    var earliest = $("#id_date").attr("data-earliest-food-date");
    var tooLate = $("#id_date").val() && !validDate();
    var pickup = $('#id_pickup').val();
    var morningOnly = pickup == 2 || pickup == 3;

    var note = "";
    if (tooLate) {
        var parts = earliest.split("-");
        var day = new Date(parts[0], parts[1] - 1, parts[2]).toLocaleDateString(
            "sv-SE", {weekday: "long", day: "numeric", month: "long"});
        note = "Om du vill beställa Jochen och/eller pastasallad måste det beställas senast onsdag 16:15 veckan innan. Välj " + day + " eller senare.";
    } else if (morningOnly) {
        note = "Om du vill beställa pastasallad och/eller fler än 100 jochen måste det hämtas på morgonen (07:30-08:00), då vi inte kan förvara dessa i våra kylar. Vänligen välj morgon som tid för upphämtning om du vill beställa dessa produkter.";
    }

    var cleared = setAvailable('Jochen', !tooLate) || !!droppedJochen;
    cleared = setAvailable('Minijochen', !tooLate) || cleared;
    cleared = setAvailable('Pastasalad', !tooLate && !morningOnly) || cleared;
    if (cleared) {
        note += " Det du hade fyllt i har tagits bort.";
    }
    $('#food_note').prop('hidden', !note).find('span').text(note);
    $('#Jochen_error').html(tooManyJochenForPickup()
        ? "<p class='text-danger mb-0'>Fler än 100 jochen måste hämtas på morgonen (07:30-08:00). Stänger du rutan tas jochen bort.</p>" : "");
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
            updateFoodAvailability();
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

        }else if(value == 2){
            changeLimit('id_numberOfCoffee', 90,'Det går inte beställa mer än 90 koppar kaffe till ' + $('#id_pickup option:selected').text()+'.');
        }else if(value == 3){
            changeLimit('id_numberOfCoffee', 135,'Det går inte beställa mer än 135 koppar kaffe till ' + $('#id_pickup option:selected').text()+ '.');
        }
        updateFoodAvailability(dropExcessJochen());
    });

    $('#JochenModal').on('hidden.bs.modal', function() {
        if (dropExcessJochen()) {
            updateFoodAvailability(true);
        }
    });

    $('#id_date').on("change", function() {
        $("#order_error").html("");
        updateFoodAvailability();
    });
    updateFoodAvailability();

    $("form").on("submit", function() {
        window.onbeforeunload = null;
    });

    calcSum();
});


