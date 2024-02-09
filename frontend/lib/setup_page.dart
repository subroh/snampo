import 'package:flutter/material.dart';
import 'package:snampo/mission_page.dart';

class SetupPage extends StatelessWidget {
  const SetupPage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textstyle = theme.textTheme.displaySmall!.copyWith(
      color: theme.colorScheme.onPrimary,
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'SETUP',
          style: textstyle,),
        centerTitle: true,
        backgroundColor: theme.colorScheme.primary,
      ),
      body: const SliderWidget(),
    );
  }
}

class SliderWidget extends StatefulWidget {
  const SliderWidget({super.key});

  @override
  _SliderWidgetState createState() => _SliderWidgetState();
}

class _SliderWidgetState extends State<SliderWidget> {
  double slidervalue = 0.5;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textstyle = theme.textTheme.displayLarge!.copyWith(
      color: theme.colorScheme.secondary,
    );
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '$slidervalue km',
            style: textstyle,),
          Slider(
            value: slidervalue,
            min: 0.5,
            max: 10.0,
            divisions: 19,
            onChanged: (value) {
              setState(() {
                slidervalue = value;
              });
            }
          ),
          const SizedBox(height: 20,),
          SubmitButton(value: slidervalue),
        ],
      ),
    );
  }
}

class SubmitButton extends StatelessWidget {
  double value;
  SubmitButton({
    required this.value,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
     final style = theme.textTheme.displayMedium!.copyWith(
      color: theme.colorScheme.onPrimary,
    );

    return ElevatedButton(
      style: ElevatedButton.styleFrom(
        backgroundColor: theme.colorScheme.primary, // ボタンの背景色
        foregroundColor: theme.colorScheme.onPrimary,
        // shape: RoundedRectangleBorder( // 形を変えるか否か
        //   borderRadius: BorderRadius.circular(10), // 角の丸み
        // ),
      ),
      onPressed: () {
        Navigator.push(
          context, 
          MaterialPageRoute(
            builder: (context) =>
            MissionPage(value),
          ),
        );
      },
      child: Padding(
        padding: const EdgeInsets.all(15.0),
        child: Text('GO', style: style),
      ),
    );
  }
}