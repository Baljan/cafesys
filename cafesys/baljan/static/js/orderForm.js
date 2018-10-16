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

    $("#form-confirmation").on('change', function () {
        var checked = $(this).is(':checked');
        $("#submit-button").prop('disabled', !checked);
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
    });

    var datepicker=$("#id_date");
    datepicker.datepicker({
        language: "sv",
        startDate: '0d',
        daysOfWeekDisabled: '06'
    });

    datepicker.datepicker().on('changeDate', function() {
        var date=$(this).datepicker('getDate').getDay();
        if (date===5) {
            if ($("#id_pickup").val() == 1){
                $("#id_pickup").val(0);
                bootbox.alert({
                  title: "OBS: Din beställning har ändrats!",
                  message: "Baljan lämnar inte ut några beställningar på fredag lunch och din upphämtningstid har därför ändrats till fredag morgon."
                });
            }
            $("option[value=1]").prop('disabled', true);

        }else{
            $("option[value=1]").prop('disabled', false);
        }
    });
});
