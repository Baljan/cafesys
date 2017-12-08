(function ($) {

  "use strict"
  // Show/Hide header when scoll + Controll classes
  var init = { previousTop: 0 }

  $(window).scroll(init, function () {
    var menuContainer = '.navbar';
    var body = $('body');
    var currentTop = $(window).scrollTop();

    if (currentTop > 90) {
      $(menuContainer).addClass('fixed');
      $(body).addClass('fixed-navbar');
    } else if (currentTop <= 0) { //56
      $(menuContainer).removeClass('fixed');
      $(body).removeClass('fixed-navbar');
    }

    var startFade = 800;

    init.previousTop = currentTop;
  });

  $('#page-wrapper a[target="_blank"]').addClass('external-link');



  // Select all links with hashes
  $('a[href*="#"]')
    // Remove links that don't actually link to anything
    .not('[href="#"]')
    .not('[href="#0"]')
    .click(function (event) {
      // On-page links

      console.log("HEJ");
      if (
        location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '')
        &&
        location.hostname == this.hostname
      ) {
        // Figure out element to scroll to
        var target = $(this.hash);
        target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
        // Does a scroll target exist?
        if (target.length) {
          // Only prevent default if animation is actually gonna happen
          event.preventDefault();
          $('html, body').animate({
            scrollTop: target.offset().top
          }, 1000, function () {
            // Callback after animation
            // Must change focus!
            var $target = $(target);
            $target.focus();
            if ($target.is(":focus")) { // Checking if the target was focused
              return false;
            } else {
              $target.attr('tabindex', '-1'); // Adding tabindex for elements not focusable
              $target.focus(); // Set focus again
            };
          });
        }
      }
    });

})(jQuery);


function bindings() {
  // add bindnings here!
    $(document).ready(function () {
      $('.hamburger').click(function () {
        $(this).toggleClass('is-active');
      });
    });
}

$(document).ready(function () {

  // Variable definitions
  $body = $('html, body');
  $window = $(window);

  bindings();
});
