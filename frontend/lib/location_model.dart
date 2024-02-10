import 'package:freezed_annotation/freezed_annotation.dart';

part 'location_model.freezed.dart';
part 'location_model.g.dart';

@freezed
abstract class LocationModel with _$LocationModel {
  factory LocationModel({
    @JsonKey(name: 'departure') LocationPoint? departure,
    @JsonKey(name: 'destination') LocationPoint? destination,
    @JsonKey(name: 'midpoints') List<LocationPoint>? midpoints,
    @JsonKey(name: 'overview_polyline') String? overviewPolyline,
  }) = _LocationModel;

  factory LocationModel.fromJson(Map<String, dynamic> json) =>
      _$LocationModelFromJson(json);
}

@freezed
abstract class LocationPoint with _$LocationPoint {
  factory LocationPoint({
    @JsonKey(name: 'latitude') double? latitude,
    @JsonKey(name: 'longitude') double? longitude,
  }) = _LocationPoint;

  factory LocationPoint.fromJson(Map<String, dynamic> json) =>
      _$LocationPointFromJson(json);
}