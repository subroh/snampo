import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

const String SERVER_URL = 'https://';

class MissionPage extends HookWidget {
  final double distance;
  const MissionPage({required this.distance, super.key});

  Future<Position> getCurrentLocation() async {
    // 現在の位置を返す
    Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high);
    return position;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textstyle = theme.textTheme.displaySmall!.copyWith(
      color: theme.colorScheme.onPrimary,
    );

    final future = useMemoized(getCurrentLocation);
    final snapshot = useFuture(future, initialData: null);

    if (snapshot.hasData && snapshot.data != null) {
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
          MapView(currentLocation: snapshot.data!),
          Center(
            child: Text(
              'Slider Value from Setup Page: $distance',
              style: const TextStyle(fontSize: 18),
            ),
          ),
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
  final Position currentLocation;
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
                  widget.currentLocation.latitude,
                  widget.currentLocation.longitude,
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
