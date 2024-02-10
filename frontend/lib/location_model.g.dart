// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'location_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$LocationModelImpl _$$LocationModelImplFromJson(Map<String, dynamic> json) =>
    _$LocationModelImpl(
      departure: json['departure'] == null
          ? null
          : LocationPoint.fromJson(json['departure'] as Map<String, dynamic>),
      destination: json['destination'] == null
          ? null
          : LocationPoint.fromJson(json['destination'] as Map<String, dynamic>),
      midpoints: (json['midpoints'] as List<dynamic>?)
          ?.map((e) => LocationPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
      overviewPolyline: json['overview_polyline'] as String?,
    );

Map<String, dynamic> _$$LocationModelImplToJson(_$LocationModelImpl instance) =>
    <String, dynamic>{
      'departure': instance.departure,
      'destination': instance.destination,
      'midpoints': instance.midpoints,
      'overview_polyline': instance.overviewPolyline,
    };

_$LocationPointImpl _$$LocationPointImplFromJson(Map<String, dynamic> json) =>
    _$LocationPointImpl(
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$$LocationPointImplToJson(_$LocationPointImpl instance) =>
    <String, dynamic>{
      'latitude': instance.latitude,
      'longitude': instance.longitude,
    };
