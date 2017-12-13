function calcSum(highlight) {
    highlight = typeof highlight !== 'undefined' ? highlight : true;
    var userInput = 30 * document.getElementById('id_numberOfJochen').value + 6 * document.getElementById('id_numberOfCoffee').value
        + 6 * document.getElementById('id_numberOfTea').value + 5 * document.getElementById('id_numberOfSoda').value
        + 6 * document.getElementById('id_numberOfKlagg').value;
    document.getElementById('currentSum').innerHTML = userInput;
    document.getElementById("id_orderSum").value = userInput;

    if (highlight) {
        $("#currentSum").effect("highlight");
    }
}


window.onload = function justdoit() {

    $("#id_sameAsOrderer").live('change', function () {
        $("#id_pickupName").effect("highlight");
        $("#id_pickupEmail").effect("highlight");
        $("#id_pickupNumber").effect("highlight");

        if ($(this).is(':checked')) {
            document.getElementById('id_pickupName').value = document.getElementById('id_orderer').value
            document.getElementById('id_pickupName').readOnly = true
            document.getElementById('id_pickupEmail').value = document.getElementById('id_ordererEmail').value
            document.getElementById('id_pickupEmail').readOnly = true
            document.getElementById('id_pickupNumber').value = document.getElementById('id_phoneNumber').value
            document.getElementById('id_pickupNumber').readOnly = true
        }
        else {
            document.getElementById('id_pickupName').value = ""
            document.getElementById('id_pickupName').readOnly = false
            document.getElementById('id_pickupEmail').value = ""
            document.getElementById('id_pickupEmail').readOnly = false
            document.getElementById('id_pickupNumber').value = ""
            document.getElementById('id_pickupNumber').readOnly = false
        }
    });

    $('#id_orderer').bind('input', function () {
        document.getElementById('id_pickupName').readOnly = true
        document.getElementById('id_pickupEmail').readOnly = true
        document.getElementById('id_pickupNumber').readOnly = true
        if (document.getElementById('id_sameAsOrderer').checked) {
            document.getElementById('id_pickupName').value = document.getElementById('id_orderer').value
        }
    });
    $('#id_ordererEmail').bind('input', function () {
        document.getElementById('id_pickupName').readOnly = true
        document.getElementById('id_pickupEmail').readOnly = true
        document.getElementById('id_pickupNumber').readOnly = true
        if (document.getElementById('id_sameAsOrderer').checked) {
            document.getElementById('id_pickupEmail').value = document.getElementById('id_ordererEmail').value
        }
    });
    $('#id_phoneNumber').bind('input', function () {
        document.getElementById('id_pickupName').readOnly = true
        document.getElementById('id_pickupEmail').readOnly = true
        document.getElementById('id_pickupNumber').readOnly = true
        if (document.getElementById('id_sameAsOrderer').checked) {
            document.getElementById('id_pickupNumber').value = document.getElementById('id_phoneNumber').value
        }
    });
}

$(function () {
    $("#check").button();
    $("#items").buttonset();
});

$("#id_jochenSelected").live('change', function () {
    if ($(this).is(':checked')) {
        $("#jochen").show("fast");
        $("#id_numberOfJochen").focus();
    }
    else {
        $("#jochen").hide("fast");
        document.getElementById('id_numberOfJochen').value = ""
        calcSum();

    }
});

$("#id_coffeeSelected").live('change', function () {
    if ($(this).is(':checked')) {
        $("#coffee").show("fast");
        $("#id_numberOfCoffee").focus();
    }
    else {
        $("#coffee").hide("fast");
        document.getElementById('id_numberOfCoffee').value = ""
        calcSum();
    }
});

$("#id_teaSelected").live('change', function () {
    if ($(this).is(':checked')) {
        $("#tea").show("fast");
        $("#id_numberOfTea").focus();
    }
    else {
        $("#tea").hide("fast");
        document.getElementById('id_numberOfTea').value = ""
        calcSum();
    }
});

$("#id_sodaSelected").live('change', function () {
    if ($(this).is(':checked')) {
        $("#soda").show("fast");
        $("#id_numberOfSoda").focus();
    }
    else {
        $("#soda").hide("fast");
        document.getElementById('id_numberOfSoda').value = ""
        calcSum();
    }
});

$("#id_klaggSelected").live('change', function () {
    if ($(this).is(':checked')) {
        $("#klagg").show("fast");
        $("#id_numberOfKlagg").focus();
    }
    else {
        $("#klagg").hide("fast");
        document.getElementById('id_numberOfKlagg').value = ""
        calcSum();
    }

});

$(document).ready(function () {
    calcSum(false);

    //	<span> {{form.orderSum.value|default_if_none:"0"}} SEK </span>
    $('#id_numberOfJochen').bind('input', function () {
        calcSum();
        //$.datepicker({minDate:+30});

    });
    $('#id_numberOfCoffee').bind('input', function () {
        calcSum();
    });
    $('#id_numberOfTea').bind('input', function () {
        calcSum();
    });
    $('#id_numberOfSoda').bind('input', function () {
        calcSum();
    });
    $('#id_numberOfKlagg').bind('input', function () {
        calcSum();
    });
});

//document.getElementById('id_orderSum').value = userInput;

$(function () {
    $("#id_date").datepicker({
        minDate: +1,
        showWeek: true,
        dateFormat: "yy-mm-dd",
        firstDay: 1,
        beforeShowDay: $.datepicker.noWeekends
    });
    $.datepicker.regional['sv'] = {
        closeText: 'Stäng',
        prevText: '&laquo;Förra',
        nextText: 'Nästa&raquo;',
        currentText: 'Idag',
        monthNames: ['Januari', 'Februari', 'Mars', 'April', 'Maj', 'Juni',
            'Juli', 'Augusti', 'September', 'Oktober', 'November', 'December'],
        monthNamesShort: ['Jan', 'Feb', 'Mar', 'Apr', 'Maj', 'Jun',
            'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dec'],
        dayNamesShort: ['Sön', 'Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör'],
        dayNames: ['Söndag', 'Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lördag'],
        dayNamesMin: ['Sö', 'Må', 'Ti', 'On', 'To', 'Fr', 'Lö'],
        weekHeader: 'Ve',
        dateFormat: 'yy-mm-dd',
        firstDay: 1,
        isRTL: false,
        showMonthAfterYear: false,
        yearSuffix: ''
    };
    $.datepicker.setDefaults($.datepicker.regional['sv']);
});
