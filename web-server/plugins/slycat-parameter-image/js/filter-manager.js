define("slycat-parameter-image-filter-manager", ["slycat-server-root", "lodash", "knockout", "knockout-mapping", "jquery"], function(server_root, _,  ko, mapping, $) {

  function FilterManager(model_id, bookmarker, layout, input_columns, output_columns, image_columns, rating_columns, category_columns) {
    var self = this;

    self.model_id = model_id;
    self.bookmarker = bookmarker;
    self.layout = layout;
    self.input_columns = input_columns;
    self.output_columns = output_columns;
    self.image_columns = image_columns;
    self.rating_columns = rating_columns;
    self.category_columns = category_columns;
    self.other_columns = null;
    self.sliders_ready = false;
    self.slidersPaneHeight = ko.observable();
    self.controls_ready = false;
  }

  /* Until AJAX handling is refactored, have to manually pass data at different times. Extremely ugly,
     but it makes these dependencies explicit and thus will be easier to decouple later. */
  FilterManager.prototype.set_bookmark = function(bookmark) {
    this.bookmark = bookmark;
  };

  /* Until AJAX handling is refactored, have to manually pass data at different times. Extremely ugly,
     but it makes these dependencies explicit and thus will be easier to decouple later. */
  FilterManager.prototype.set_other_columns = function(other_columns) {
    this.other_columns = other_columns;
  };

  /* Until AJAX handling is refactored, have to manually pass data at different times. Extremely ugly,
     but it makes these dependencies explicit and thus will be easier to decouple later. */
  FilterManager.prototype.set_table_metadata = function(table_metadata) {
    this.table_metadata = table_metadata;
  };

  /* Until AJAX handling is refactored, have to manually pass data at different times. Extremely ugly,
     but it makes these dependencies explicit and thus will be easier to decouple later. */
  FilterManager.prototype.notify_controls_ready = function() {
    this.controls_ready = true;
  };

  FilterManager.prototype.build_sliders = function(controls_ready) {
    var self = this;
    if (!self.sliders_ready && self.controls_ready && self.table_metadata) {
      self.sliders_ready = true;
      $("#sliders-pane .load-status").css("display", "none");

      var variable_order = self.input_columns.concat(self.output_columns, self.rating_columns, self.category_columns, self.other_columns);
      var numeric_variables = [];
      for (var i = 0; i < self.table_metadata["column-count"]; i++) {
        if (self.table_metadata["column-types"][i] != 'string' && !(_.includes(self.category_columns, i)) && self.table_metadata["column-count"]-1 > i) {
          numeric_variables.push(i);
        }
      }

      var allFilters = ko.observableArray();
      var numericFilters, categoryFilters;

      // have to be built after allFilters is assigned, and it's reassigned from bookmark,
      // so call this from both conditional clauses
      var buildComputedFilters = function(filters) {
        numericFilters = ko.pureComputed(function() {
          return _.filter(filters(), function(f) { return f.type() === 'numeric'; });
        });
        categoryFilters = ko.pureComputed(function() {
          return _.filter(filters(), function(f) { return f.type() === 'category'; });
        });
      };

      var rateLimit = 500;
      if ("allFilters" in self.bookmark) {
        allFilters = mapping.fromJS(self.bookmark["allFilters"]);
        buildComputedFilters(allFilters);

        _.each(numericFilters, function (filter) {
          filter.rateLimitedHigh = ko.pureComputed( allFilters()[i].high ).extend({ rateLimit: { timeout: rateLimit, method: "notifyWhenChangesStop" } });
          filter.rateLimitedLow = ko.pureComputed( allFilters()[i].low ).extend({ rateLimit: { timeout: rateLimit, method: "notifyWhenChangesStop" } });
        });
      }
      else {
        _.each(self.category_columns, function(i) {
          allFilters.push({
            name: ko.observable( self.table_metadata["column-names"][i] ),
            type: ko.observable('category'),
            index: ko.observable( i ),
            active: ko.observable(false),
            order: ko.observable(100) // always put category filters on the right
          });
        });

        _.each(numeric_variables, function(i) {
          var high = ko.observable( self.table_metadata["column-max"][i] );
          var low = ko.observable( self.table_metadata["column-min"][i] );
          allFilters.push({
            name: ko.observable( self.table_metadata["column-names"][i] ),
            type: ko.observable('numeric'),
            index: ko.observable( i ),
            max: ko.observable( self.table_metadata["column-max"][i] ),
            min: ko.observable( self.table_metadata["column-min"][i] ),
            high: high,
            low: low,
            invert: ko.observable(false),
            active: ko.observable(false),
            order: ko.observable( variable_order.indexOf(i) ),
            rateLimitedHigh: ko.pureComputed(high).extend({ rateLimit: { timeout: rateLimit, method: "notifyWhenChangesStop" } }),
            rateLimitedLow: ko.pureComputed(low).extend({ rateLimit: { timeout: rateLimit, method: "notifyWhenChangesStop" } }),
          });
        });

        buildComputedFilters(allFilters);
      }

      var ViewModel = function(params) {
        var vm = this;
        self.slidersPaneHeight( $("#sliders-pane").innerHeight() );
        vm.sliderHeight = ko.pureComputed(function() {
          return self.slidersPaneHeight() - 95;
        }, this);
        vm.thumb_length = ko.observable(12);
        vm.allFilters = allFilters;
        vm.numericFilters = numericFilters;
        vm.categoryFilters = categoryFilters;
        vm.availableFilters = ko.observableArray(
          vm.allFilters.slice(0).sort(function(one, two) {
            return one.order() < two.order() ? -1 : 1;
          })
        );

        // TODO make pureComputed?
        vm.activeNumericFilters = vm.allFilters.filter(function(filter) {
          return filter.type() === 'numeric' && filter.active();
        });
        vm.activeCategoryFilters = vm.allFilters.filter(function(filter) {
          return filter.type() === 'category' && filter.active();
        });

        if (vm.activeNumericFilters().length > 0 || vm.activeCategoryFilters().length > 0) {
          self.layout.open("west");
        }

        _.each(vm.numericFilters(), function (filter) {
          filter.rateLimitedHigh.subscribe(function(newValue) {
            // console.log("rateLimitedHighValue is: " + newValue);
            self.bookmarker.updateState( {"allFilters" : mapping.toJS(vm.allFilters())} );
          });
          filter.rateLimitedLow.subscribe(function(newValue) {
            // console.log("rateLimitedLowValue is: " + newValue);
            self.bookmarker.updateState( {"allFilters" : mapping.toJS(vm.allFilters())} );
          });
        });

        vm.activateFilter = function(item, event) {
          if (vm.activeNumericFilters().length === 0 && vm.activeCategoryFilters().length === 0) {
            self.layout.open("west");
          }
          var activateFilter = event.target.value;
          _.each(vm.allFilters(), function (filter) {
            if (filter.index() == Number(activateFilter)) {
              // Move it to the end of the array
              vm.allFilters.push( vm.allFilters.remove(filter)[0] );
              // Show it
              filter.active(true);
            }
          });

          event.target.selectedIndex = 0;
          $("#sliders-pane #sliders .slycat-pim-filter:last-child").get(0).scrollIntoView();
          self.bookmarker.updateState( {"allFilters" : mapping.toJS(vm.allFilters())} );
        };
        vm.removeFilter = function(item, event) {
          var filterIndex = vm.allFilters.indexOf(item);
          vm.allFilters()[filterIndex].active(false);
          if (vm.activeNumericFilters().length == 0 && vm.activeCategoryFilters().length == 0) {
            self.layout.close("west");
          }
          self.bookmarker.updateState( {"allFilters" : mapping.toJS(vm.allFilters())} );
        };
        vm.invertFilter = function(item, event) {
          var filterIndex = vm.allFilters.indexOf(item);
          vm.allFilters()[filterIndex].invert( !vm.allFilters()[filterIndex].invert() );
          self.bookmarker.updateState( {"allFilters" : mapping.toJS(vm.allFilters())} );
        };
      };

      ko.applyBindings(
        new ViewModel(),
        document.getElementById('parameter-image-plus-layout')
      );
    }
  };

  return FilterManager;
});