import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:dio/dio.dart';
import 'package:provider/provider.dart';
import 'package:snampo/snap_menu.dart';
import 'package:snampo/provider.dart';
import 'package:snampo/location_model.dart';

const String SERVER_URL = 'https://';

class MissionPage extends HookWidget {
  final double radius;
  const MissionPage({required this.radius, super.key});

  // Future<Position> getCurrentLocation() async {
  //   // 現在の位置を返す
  //   Position position = await Geolocator.getCurrentPosition(
  //       desiredAccuracy: LocationAccuracy.high);
  //   print("got current location");
  //   return position;
  // }

  // Future<String> getMissionInfo(Position position) async {
  //   final dio = Dio();
  //   String radiusString =
  //       (radius * 10000).toInt().toString(); // km から m にし整数値の文字列に
  //   print("made query");
  //   final response = await dio.get(
  //     'http://localhost:80/route',
  //     queryParameters: {
  //       'currentLat': position.latitude,
  //       'currentLng': position.longitude,
  //       'radius': radiusString,
  //     },
  //   );
  //   // String response = '{"departure":{"latitude":35.658581,"longitude":139.745433},"destination":{"latitude":35.65946095725984,"longitude":139.73649146904035},"midpoints":[{"latitude":35.657320000000006,"longitude":139.74216}],"overview_polyline":"orsxEaa}sYAAP_@f@eAj@f@XXn@b@RFPAd@M|@UJBF|@PtB@Jm@ZPn@FTo@VNl@@DKF\\nALf@@REv@DBANEAC\\EbACJICGVc@rB]zBOnA[|BMv@INGr@?Z@z@HTHHNNp@tAJ`@BV@x@KxAGn@E^QDBXJC?ZE@DRu@TBBC@UHQ@SA}@GcC[y@O"}';
  //   print("got response");
  //   return (response.data);

  //   // } catch (e) {
  //   //   return ('Error: $e');
  //   // }
  // }

  // Future<LocationModel> loadJsonData(missionInfo) async {
  //   String jsonString = missionInfo;
  //   Map<String, dynamic> jsonData = json.decode(jsonString);
  //   print("loaded json");
  //   return LocationModel.fromJson(jsonData);
  // }

  // Future<LocationModel> makeMission() async {
  //   Position currentLocation = await getCurrentLocation();
  //   String missionInfo = await getMissionInfo(currentLocation);
  //   LocationModel locationModel = await loadJsonData(missionInfo);
  //   return locationModel;
  // }

  Future<LocationModel> makeMission() async {
    Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high);
    
    final dio = Dio();
    String radiusString =
        (radius * 10000).toInt().toString(); // km から m にし整数値の文字列に
    print("made query");
    // final response = await dio.get(
    //   'http://localhost:80/route',
    //   queryParameters: {
    //     'currentLat': position.latitude,
    //     'currentLng': position.longitude,
    //     'radius': radiusString,
    //   },
    // );
    const response = '{"departure":{"latitude":35.658581,"longitude":139.745433},"destination":{"latitude":35.65946095725984,"longitude":139.73649146904035},"midpoints":[{"latitude":35.657320000000006,"longitude":139.74216}],"overview_polyline":"orsxEaa}sYAAP_@f@eAj@f@XXn@b@RFPAd@M|@UJBF|@PtB@Jm@ZPn@FTo@VNl@@DKF\\nALf@@REv@DBANEAC\\EbACJICGVc@rB]zBOnA[|BMv@INGr@?Z@z@HTHHNNp@tAJ`@BV@x@KxAGn@E^QDBXJC?ZE@DRu@TBBC@UHQ@SA}@GcC[y@O"}';
    String jsonString = response;
    Map<String, dynamic> jsonData = await jsonDecode(jsonString);
    print("loaded json");
    LocationModel missionInfo = LocationModel.fromJson(jsonData);
    return missionInfo;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textstyle = theme.textTheme.displaySmall!.copyWith(
      color: theme.colorScheme.onPrimary,
    );

    // final future = useMemoized(getCurrentLocation);
    final future = useMemoized(makeMission);
    final snapshot = useFuture(future, initialData: null);

    if (snapshot.hasData && snapshot.data != null) {
      final LocationModel missionInfo = snapshot.data!;
      target = missionInfo.destination;
      route = missionInfo.overviewPolyline;
      landmarkInfoList = missionInfo.midpoints;

      return Scaffold(
        appBar: AppBar(
          title: Text(
            'On MISSION',
            style: textstyle,
          ),
          centerTitle: true,
          backgroundColor: theme.colorScheme.primary,
        ),
        body: Stack(children: [
          MapView(currentLocation: missionInfo.departure!),
          Center(
            child: Text(
              'Slider Value from Setup Page: $radius',
              style: const TextStyle(fontSize: 18),
            ),
          ),
          SnapView(),
        ]),
      );
    } else if (snapshot.hasError) {
      return const Center(
        child: Text('error occurred'),
      );
    } else {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            'On MISSION',
            style: textstyle,
          ),
          centerTitle: true,
          backgroundColor: theme.colorScheme.primary,
        ),
        body: const Center(
          child: Column(
            children: [
              Text("NOW LOADING"),
            ],
          ),
        ),
      );
    }
  }
}

class MapView extends StatefulWidget {
  final LocationPoint currentLocation;
  const MapView({required this.currentLocation, super.key});

  @override
  _MapViewState createState() => _MapViewState();
}

class _MapViewState extends State<MapView> {
  // マップの表示制御用
  late GoogleMapController mapController;

  @override
  Widget build(BuildContext context) {
    // 画面の幅と高さを決定する
    var height = MediaQuery.of(context).size.height;
    var width = MediaQuery.of(context).size.width;

    return SizedBox(
      height: height,
      width: width,
      child: Scaffold(
        body: Stack(
          children: <Widget>[
            GoogleMap(
              initialCameraPosition: CameraPosition(
                //マップの初期位置を指定
                zoom: 17, //ズーム
                target: LatLng(
                  //緯度, 経度
                  widget.currentLocation.latitude!,
                  widget.currentLocation.longitude!,
                ),
              ),
              myLocationEnabled: true,
              myLocationButtonEnabled: false,
              mapType: MapType.normal,
              zoomGesturesEnabled: true,
              zoomControlsEnabled: false,
              onMapCreated: (GoogleMapController controller) {
                mapController = controller;
              },
            ),
          ],
        ),
      ),
    );
  }
}
