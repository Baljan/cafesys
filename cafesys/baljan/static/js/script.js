$(function (){
  $("#id_sameAsOrderer").on("change", function () {
    if($(this).is(":checked")) {
      $("#id_pickupName, #id_pickupEmail, #id_pickupNumber").attr("disabled", "disabled");
      $("#id_pickupName, #id_pickupEmail, #id_pickupNumber").val("");
      $("#id_orderer, #id_ordererEmail, #id_phoneNumber").bind("input", function () {
        $($(this).data("pickup")).val($(this).val());
      });

      $("#id_orderer, #id_ordererEmail, #id_phoneNumber").each(function () {
        $($(this).data("pickup")).val($(this).val());
      });
    }
    else {
      $("#id_pickupName, #id_pickupEmail, #id_pickupNumber").removeAttr("disabled");
      $("#id_orderer, #id_ordererEmail, #id_phoneNumber").unbind("input");
    }
  });

  $("#id_orderer, #id_ordererEmail, #id_phoneNumber").bind("input", function () {
    $($(this).data("pickup")).val($(this).val());
  });

  $(".product").bind("input", function () {
    var quantity = parseInt($(this).val());
    if (isNaN(quantity) || quantity < 0) {
      $(this).val("");
    }

    calculateSum();
  });

  $("input[name=selected-products]").bind("change", function () {
    calculateSum();
  });

  $('[data-tooltip="menu"]').tooltip({'placement': 'bottom', 'trigger': 'hover'});


  $('.input-group.date').datepicker({
    autoclose: true,
    format: "yyyy-mm-dd",
    weekStart: 1,
    startDate: "0",
    endDate: "2015-12-18",
    maxViewMode: 1,
    todayBtn: "linked",
    language: "sv",
    daysOfWeekDisabled: "0,6",
    calendarWeeks: true,
    todayHighlight: true
    //datesDisabled: ['12/06/2015', '12/21/2015']
  });
  
      /* Semester Administration */
    if ($("body").hasClass('admin-semester')) {
        var editShiftsForm = $('form[name=edit-shifts]'),
            shiftInners = $('table td.shift div');

        $('table').unselectable();
        $('.months').selectable({
            filter: 'td.shift',
            stop: function(ev, ui) {
                var inputs = editShiftsForm.find('input[type=button]');
                if ($('table td.ui-selected').length) {
                    $(inputs).removeAttr('disabled');
                }
                else {
                    $(inputs).attr('disabled', 'disabled');
                }
            }
        });

        $(shiftInners).hover(function() {
            var comb = $(this).html();
            if (comb == '&nbsp;') return;
            $(shiftInners).filter(function() {
                return $(this).html() == comb;
            }).addClass('highlight');
        }, function() {
            var comb = $(this).html();
            if (comb == '&nbsp;') return;
            $(shiftInners).filter(function() {
                return $(this).html() == comb;
            }).removeClass('highlight');
        });

        $('input[name=start]').datepicker({ // TODO: i18n
            dateFormat:"yy-mm-dd",
            changeMonth: true,
            changeYear: true
        });
        $('input[name=end]').datepicker({ // TODO: i18n
            dateFormat:"yy-mm-dd",
            changeMonth: true,
            changeYear: true
        });

        var newSemDialogButtons = {};
        newSemDialogButtons[SAVE_MSG] = function() {
            $(this).find('form').submit();
        }
        newSemDialogButtons[CANCEL_MSG] = function() {
            $(this).dialog('close');
        }
        var newSemDialog = $('#new-sem-dialog').dialog({
            modal: true,
            autoOpen: false,
            buttons: newSemDialogButtons,
            width: 500
        });
        $('.show-new-sem-dialog').click(function() {
            newSemDialog.dialog('open');
        });
        if (NEW_SEMESTER_FAILED) {
            $('.show-new-sem-dialog').click();
        }
        $('.selection input').click(function() {
            editShiftsForm.find('input[name=make]').attr('value', $(this).attr('class'));
            var shiftIds = [];
            $('table td.ui-selected').each(function() {
                shiftIds.push(parseInt($(this).attr('id').split('-')[1], 10));
            });
            editShiftsForm.find('input[name=shift-ids]')
                          .attr('value', shiftIds.join('|'));

            if (confirm(CONFIRM_MSG)) {
                editShiftsForm.submit();
            }
        });

        $('.choose-semester select').change(function() {
            var name = $(this).children(':selected').html();
            location.href = '' + BASE_URL + '/' + name;
        });
    }
});

function calculateSum() {
  var sum = 0;
  $("input[name=selected-products]:checked").each(function () {
    var target = $($(this).parent().data("target") + " input");
    sum += $(target).val() * $(target).data("price");
  });
  $("#sum").html(sum + " " + $("#sum").data("currency"));
}

function initialize() {
  var baljanLatLng = new google.maps.LatLng(58.4008713, 15.578388);

  var map = new google.maps.Map(document.getElementById('map-container'), {
    center: baljanLatLng,
    zoom: 18,
    scrollwheel: false,
    mapTypeControl: false,
    streetViewControl: false,
    styles: [{
      featureType: "poi",
      elementType: "labels",
      stylers: [
              { visibility: "off" }
        ]
    },{
      featureType: "transit",
      elementType: "labels",
      stylers: [
              { visibility: "off" }
        ]
    }]
  });

  var infowindow = new google.maps.InfoWindow();
  /*var service = new google.maps.places.PlacesService(map);

  service.getDetails({placeId: 'ChIJEVWHH29vWUYRxtSDTcmejw8'}, function(place, status) {
    if (status == google.maps.places.PlacesServiceStatus.OK) {
      var marker = new google.maps.Marker({
        map: map,
        position: place.geometry.location
      });
      google.maps.event.addListener(marker, 'click', function() {
        infowindow.setContent(place.name);
        infowindow.open(map, this);
      });
    }
  });*/
  
   var marker = new google.maps.Marker({
    map: map,
    position: baljanLatLng,
    title: "Sektionscafé Baljan"
  });
  var content = 
      '<div class="iw-container">\
<div class="iw-title">Sektionscafé Baljan</div>\
<div class="iw-content">\
<ul class="list-unstyled">\
<li><a href="https://www.facebook.com/sektionscafe.baljan">Facebook</a></li>\
<li><a href="https://twitter.com/liu_baljan">Twitter</a></li>\
<li><a href="#">Google Plus</a></li>\
</ul>\
  </div>\
  </div>';
  google.maps.event.addListener(marker, 'click', function() {
    infowindow.setContent(content);
    infowindow.open(map, this);
  });
}

google.maps.event.addDomListener(window, 'load', initialize);

